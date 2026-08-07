import difflib
import mimetypes
from uuid import UUID

import requests
import structlog
from django.contrib.auth.models import Permission
from django.db import models, transaction
from django.forms import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import (
    FileUploadParser,
    FormParser,
    JSONParser,
    MultiPartParser,
)
from rest_framework.response import Response
import weasyprint
from weasyprint import HTML

import django_filters as df

from core.net_safety import BlockedRequestError, assert_public_url
from core.validators import validate_file_name, validate_file_size
from core.views import BaseModelViewSet, GenericFilterSet
from iam.models import RoleAssignment, Folder

from .models import (
    DocumentAttachment,
    DocumentContainer,
    DocumentEdit,
    DocumentRevision,
    DocumentTemplate,
    ManagedDocument,
)


class DocumentTemplateViewSet(BaseModelViewSet):
    """CRUD for reusable document content templates (built-in + custom)."""

    model = DocumentTemplate
    filterset_fields = [
        "document_type",
        "folder",
        "locale",
        "builtin",
        "ref_id",
        "provider",
    ]
    serializers_module = "doc_management.serializers"

    @action(detail=False, name="Get locale choices")
    def locale(self, request):
        locales = DocumentTemplate.objects.values_list("locale", flat=True).distinct()
        return Response({loc: loc for loc in sorted(set(filter(None, locales)))})

    @action(detail=False, methods=["post"], url_path="import")
    def import_templates(self, request):
        """Bulk-import custom templates from a .zip of ``<locale>/<name>.md``
        files (same layout as the built-in library)."""
        import zipfile

        from .template_import import import_templates_from_zip

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not uploaded.name.lower().endswith(".zip"):
            return Response(
                {"file": "invalidFileType"}, status=status.HTTP_400_BAD_REQUEST
            )

        folder_id = request.data.get("folder")
        folder = Folder.objects.filter(id=folder_id).first() if folder_id else None
        if folder is None:
            folder = Folder.get_root_folder()

        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_documenttemplate"),
            folder=folder,
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            result = import_templates_from_zip(uploaded, folder)
        except zipfile.BadZipFile:
            return Response({"file": "invalidZip"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


from .serializers import DocumentContainerReadSerializer

logger = structlog.get_logger(__name__)


def _get_user_lang(request):
    """Get the user's preferred language from their preferences."""
    if hasattr(request, "user") and hasattr(request.user, "get_preferences"):
        return request.user.get_preferences().get("lang", "en")
    return "en"


_PDF_FETCH_MAX_BYTES = 10 * 1024 * 1024


# WeasyPrint passes a configured `ssl_context` we don't thread through:
# deployments needing a custom CA for embedded images won't get it. File
# an issue if that becomes a real need.
def _safe_url_fetcher(url, timeout=10, ssl_context=None):
    if url.startswith("data:"):
        return weasyprint.default_url_fetcher(url)
    assert_public_url(url, allowed_schemes=("https",))
    r = requests.get(url, timeout=timeout, allow_redirects=False, stream=True)
    try:
        status_code = r.status_code
        final_url = r.url
        content_type = r.headers.get("Content-Type", "application/octet-stream")
        if 300 <= status_code < 400:
            raise BlockedRequestError(f"Redirects not followed: {url}")
        content = r.raw.read(_PDF_FETCH_MAX_BYTES + 1, decode_content=True)
    finally:
        r.close()
    if len(content) > _PDF_FETCH_MAX_BYTES:
        raise BlockedRequestError(f"Response exceeds {_PDF_FETCH_MAX_BYTES} bytes")
    mime = content_type.split(";")[0].strip() or None
    return {"string": content, "mime_type": mime, "redirected_url": final_url}


class DocumentContainerFilter(GenericFilterSet):
    # Container status = its default-locale document's current-revision status
    # (matches the `status` shown in the read serializer / table).
    status = df.MultipleChoiceFilter(
        choices=DocumentRevision.Status.choices, method="filter_status"
    )
    source = df.MultipleChoiceFilter(
        choices=DocumentRevision.Source.choices, method="filter_source"
    )

    class Meta:
        model = DocumentContainer
        fields = [
            "document_type",
            "folder",
            "classification",
            "filtering_labels",
            "policies",
            "applied_controls",
            "task_templates",
            "processings",
        ]

    def filter_status(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            documents__default_locale=True,
            documents__current_revision__status__in=value,
        ).distinct()

    def filter_source(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            documents__default_locale=True,
            documents__current_revision__source__in=value,
        ).distinct()


class DocumentContainerViewSet(BaseModelViewSet):
    """
    API endpoint that allows document containers (the language-independent
    identity of a managed document) to be viewed or edited.
    """

    model = DocumentContainer
    filterset_class = DocumentContainerFilter
    search_fields = ["name", "ref_id"]
    serializers_module = "doc_management.serializers"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("folder", "classification")
            .prefetch_related(
                "policies",
                "applied_controls",
                "task_templates",
                "processings",
                models.Prefetch(
                    "documents",
                    queryset=ManagedDocument.objects.select_related("current_revision"),
                ),
            )
        )

    @action(detail=False, name="Get document type choices")
    def document_type(self, request):
        return Response(
            [
                {"value": v, "label": str(label)}
                for v, label in DocumentContainer.DocumentType.choices
            ]
        )

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(
            [
                {"value": v, "label": str(label)}
                for v, label in DocumentRevision.Status.choices
            ]
        )

    @action(detail=False, name="Get source choices")
    def source(self, request):
        return Response(
            [
                {"value": v, "label": str(label)}
                for v, label in DocumentRevision.Source.choices
            ]
        )

    @action(detail=True, methods=["get"])
    def references(self, request, pk=None):
        """Computed doc-to-doc references for a container: outgoing (this links
        to) and incoming (linked from)."""
        container = self.get_object()
        accessible = set(
            RoleAssignment.get_accessible_object_ids(
                Folder.get_root_folder(), request.user, DocumentContainer
            )[0]
        )
        outgoing = [
            {"id": str(r.target_container_id), "str": r.target_container.name}
            for r in container.outgoing_references.select_related("target_container")
            if r.target_container_id in accessible
        ]
        incoming = [
            {"id": str(r.source_container_id), "str": r.source_container.name}
            for r in container.incoming_references.select_related("source_container")
            if r.source_container_id in accessible
        ]
        return Response({"references": outgoing, "referenced_by": incoming})

    @action(detail=False, methods=["get"])
    def catalog(self, request):
        """Reading catalog: one entry per container that has at least one
        published revision, with the latest published revision per locale."""
        containers = (
            self.get_queryset()
            .select_related("classification")
            .prefetch_related("documents__revisions", "folder")
            .distinct()
        )
        result = []
        for c in containers:
            languages = []
            for doc in c.documents.all():
                # Use the prefetched revisions; filter()/order_by() would re-query.
                published = [
                    r
                    for r in doc.revisions.all()
                    if r.status == DocumentRevision.Status.PUBLISHED
                ]
                pub = max(published, key=lambda r: r.version_number, default=None)
                if pub:
                    languages.append(
                        {
                            "locale": doc.locale,
                            "default_locale": doc.default_locale,
                            "document_id": str(doc.id),
                            "revision_id": str(pub.id),
                            "version_number": pub.version_number,
                            "published_at": pub.published_at,
                            "source": pub.source,
                            "has_pdf": bool(pub.pdf_snapshot),
                            "has_file": bool(pub.file),
                            "url": pub.url,
                        }
                    )
            if not languages:
                continue
            languages.sort(key=lambda x: (not x["default_locale"], x["locale"]))
            result.append(
                {
                    "id": str(c.id),
                    "ref_id": c.ref_id,
                    "name": c.name,
                    "document_type": c.document_type,
                    "folder": {"id": str(c.folder_id), "str": c.folder.name}
                    if c.folder_id
                    else None,
                    "classification": {
                        "abbreviation": c.classification.abbreviation,
                        "hexcolor": c.classification.hexcolor,
                        "name": c.classification.label,
                    }
                    if c.classification_id
                    else None,
                    "languages": languages,
                }
            )
        return Response(result)

    @action(
        detail=False,
        methods=["post"],
        url_path="upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload(self, request):
        """Create a document from an uploaded file, bypassing the markdown editor.
        The file is stored as a published 'uploaded' revision so it appears in the
        reading catalog immediately."""
        upload = request.data.get("file")
        if not upload:
            return Response({"file": "Required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_file_size(upload)
            validate_file_name(upload)
        except DjangoValidationError as e:
            return Response({"file": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        folder_id = request.data.get("folder")
        try:
            folder = Folder.objects.get(id=folder_id)
        except Folder.DoesNotExist, DjangoValidationError, ValueError:
            return Response(
                {"folder": "Required / not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_documentcontainer"),
            folder=folder,
        ):
            return Response(
                {"folder": "You do not have permission to add documents here."},
                status=status.HTTP_403_FORBIDDEN,
            )

        document_type = (
            request.data.get("document_type") or DocumentContainer.DocumentType.POLICY
        )
        if document_type not in DocumentContainer.DocumentType.values:
            return Response(
                {"document_type": "Invalid."}, status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            container = DocumentContainer.objects.create(
                document_type=document_type,
                name=request.data.get("name") or getattr(upload, "name", ""),
                folder=folder,
                is_published=False,
            )
            document = ManagedDocument.objects.create(
                container=container,
                locale=request.data.get("locale") or "en",
                default_locale=True,
            )
            # Starts as a draft — goes through the same review/publish lifecycle
            # as authored documents.
            revision = DocumentRevision.objects.create(
                document=document,
                version_number=1,
                source=DocumentRevision.Source.UPLOADED,
                file=upload,
                status=DocumentRevision.Status.DRAFT,
                author=request.user if request.user.is_authenticated else None,
            )
            document.current_revision = revision
            document.save()
        return Response(
            DocumentContainerReadSerializer(
                container, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="link")
    def link(self, request):
        """Create a document that points at an external URL, versioned and
        lifecycle-managed like authored/uploaded documents."""
        from django.core.validators import URLValidator

        url = (request.data.get("url") or "").strip()
        try:
            URLValidator(schemes=["http", "https"])(url)
        except DjangoValidationError:
            return Response(
                {"url": "Enter a valid http(s) URL."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        folder_id = request.data.get("folder")
        try:
            folder = Folder.objects.get(id=folder_id)
        except Folder.DoesNotExist, DjangoValidationError, ValueError:
            return Response(
                {"folder": "Required / not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_documentcontainer"),
            folder=folder,
        ):
            return Response(
                {"folder": "You do not have permission to add documents here."},
                status=status.HTTP_403_FORBIDDEN,
            )

        document_type = (
            request.data.get("document_type") or DocumentContainer.DocumentType.POLICY
        )
        if document_type not in DocumentContainer.DocumentType.values:
            return Response(
                {"document_type": "Invalid."}, status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            container = DocumentContainer.objects.create(
                document_type=document_type,
                name=request.data.get("name") or "",
                folder=folder,
                is_published=False,
            )
            document = ManagedDocument.objects.create(
                container=container,
                locale=request.data.get("locale") or "en",
                default_locale=True,
            )
            revision = DocumentRevision.objects.create(
                document=document,
                version_number=1,
                source=DocumentRevision.Source.LINK,
                url=url,
                status=DocumentRevision.Status.DRAFT,
                author=request.user if request.user.is_authenticated else None,
            )
            document.current_revision = revision
            document.save()
        return Response(
            DocumentContainerReadSerializer(
                container, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="add-locale",
        parser_classes=[JSONParser, MultiPartParser, FormParser],
    )
    def add_locale(self, request, pk=None):
        """Add a new locale variant to this container with its first revision
        (link or uploaded) in a single transaction. Atomic on purpose: creating
        the locale document and then attaching the link/file as two calls could
        leave an orphaned empty authored document if the second call failed."""
        from django.core.validators import URLValidator

        # get_object() enforces add_documentcontainer on the container's folder.
        container = self.get_object()

        locale = (request.data.get("locale") or "").strip()
        if not locale:
            return Response({"locale": "Required."}, status=status.HTTP_400_BAD_REQUEST)

        source = request.data.get("source")
        if source == DocumentRevision.Source.LINK:
            url = (request.data.get("url") or "").strip()
            try:
                URLValidator(schemes=["http", "https"])(url)
            except DjangoValidationError:
                return Response(
                    {"url": "Enter a valid http(s) URL."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            revision_fields = {"source": DocumentRevision.Source.LINK, "url": url}
        elif source == DocumentRevision.Source.UPLOADED:
            upload = request.data.get("file")
            if not upload:
                return Response(
                    {"file": "Required."}, status=status.HTTP_400_BAD_REQUEST
                )
            try:
                validate_file_size(upload)
                validate_file_name(upload)
            except DjangoValidationError as e:
                return Response(
                    {"file": e.messages}, status=status.HTTP_400_BAD_REQUEST
                )
            revision_fields = {
                "source": DocumentRevision.Source.UPLOADED,
                "file": upload,
            }
        else:
            return Response(
                {"source": "Must be 'link' or 'uploaded'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            siblings = ManagedDocument.objects.select_for_update().filter(
                container=container
            )
            if siblings.filter(locale=locale).exists():
                return Response(
                    {"locale": "This language already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            document = ManagedDocument.objects.create(
                container=container,
                locale=locale,
                folder=container.folder,
                default_locale=not siblings.exists(),
            )
            revision = DocumentRevision.objects.create(
                document=document,
                version_number=1,
                status=DocumentRevision.Status.DRAFT,
                author=request.user if request.user.is_authenticated else None,
                **revision_fields,
            )
            document.current_revision = revision
            document.save()
        return Response(
            {
                "id": str(document.id),
                "locale": document.locale,
                "revision_id": str(revision.id),
            },
            status=status.HTTP_201_CREATED,
        )


class ManagedDocumentViewSet(BaseModelViewSet):
    """
    API endpoint that allows managed documents to be viewed or edited.
    """

    model = ManagedDocument
    filterset_fields = [
        "container",
        "folder",
        "locale",
        "container__policies",
        "container__document_type",
    ]
    serializers_module = "doc_management.serializers"

    @action(detail=False, methods=["get"])
    def templates(self, request):
        """List available document templates (DB-backed) for a language, falling
        back to English when the requested language has none."""
        lang = request.query_params.get("lang") or _get_user_lang(request)
        document_type = request.query_params.get("document_type")

        # Folder-scope to templates the user can access; built-ins are the shared
        # library and stay visible regardless of domain.
        # TODO(revisit): custom templates in Global aren't shared to domain-only
        # users (only built-ins are). If Global should act as a shared library,
        # also OR in root-folder templates here.
        accessible_ids = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, DocumentTemplate
        )[0]

        def for_locale(locale):
            qs = DocumentTemplate.objects.filter(locale=locale).filter(
                models.Q(id__in=accessible_ids) | models.Q(builtin=True)
            )
            if document_type:
                qs = qs.filter(document_type=document_type)
            return qs

        # Fall back to English per (locale, type), not all-or-nothing: an English
        # template of the requested type shows even when the locale has other types.
        qs = for_locale(lang)
        if not qs.exists() and lang != "en":
            qs = for_locale("en")
        templates = [
            {
                "id": t.ref_id,
                "title": t.name,
                "description": t.description,
                "provider": t.provider,
                "lang": t.locale,
                "document_type": t.document_type,
                "builtin": t.builtin,
            }
            for t in qs.order_by("name")
        ]
        return Response(templates)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-image",
        parser_classes=[MultiPartParser, FormParser, FileUploadParser],
    )
    def upload_image(self, request, pk=None):
        """Upload an image file and attach it to this document."""
        document = self.get_object()
        # FileUploadParser puts file in request.data['file'], MultiPartParser in request.FILES['file']
        uploaded_file = request.FILES.get("file") or request.data.get("file")
        if not uploaded_file:
            return Response(
                {"error": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Only allow safe raster image formats (no SVG/HTML which could be XSS vectors)
        ALLOWED_IMAGE_TYPES = {
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
        }
        content_type = (uploaded_file.content_type or "").lower()
        if content_type not in ALLOWED_IMAGE_TYPES:
            return Response(
                {"error": "Only PNG, JPEG, GIF, and WebP images are allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        attachment = DocumentAttachment(
            document=document,
            file=uploaded_file,
            uploaded_by=request.user,
        )
        try:
            attachment.full_clean()
        except DjangoValidationError as e:
            messages = []
            if hasattr(e, "message_dict"):
                for field_messages in e.message_dict.values():
                    messages.extend(field_messages)
            elif hasattr(e, "messages"):
                messages = e.messages
            else:
                messages = [str(e.message)]
            return Response(
                {"error": " ".join(messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        attachment.save()
        return Response(
            {
                "id": str(attachment.id),
                "url": f"/document-attachments/{attachment.id}/file/",
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="create-new-draft")
    def create_new_draft(self, request, pk=None):
        """Create a new draft revision cloned from the current revision."""
        from django.db import transaction

        document = self.get_object()
        source = document.current_revision
        if not source:
            source = document.revisions.first()
        content = source.content if source else ""

        with transaction.atomic():
            # Lock existing revisions to serialize draft creation and version numbering
            revisions_qs = DocumentRevision.objects.select_for_update().filter(
                document=document
            )
            if revisions_qs.filter(status=DocumentRevision.Status.DRAFT).exists():
                return Response(
                    {"error": "A draft revision already exists for this document."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            max_version = (
                revisions_qs.aggregate(models.Max("version_number"))[
                    "version_number__max"
                ]
                or 0
            )
            revision = DocumentRevision.objects.create(
                document=document,
                version_number=max_version + 1,
                content=content,
                author=request.user,
                status=DocumentRevision.Status.DRAFT,
            )
        return Response(
            {
                "id": str(revision.id),
                "version_number": revision.version_number,
                "status": revision.status,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-revision",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_revision(self, request, pk=None):
        """Upload a file as a new draft revision — or replace the current draft's
        file. Uploaded revisions follow the same review/publish lifecycle."""
        document = self.get_object()
        upload = request.data.get("file")
        if not upload:
            return Response({"file": "Required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_file_size(upload)
            validate_file_name(upload)
        except DjangoValidationError as e:
            return Response({"file": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            revisions_qs = DocumentRevision.objects.select_for_update().filter(
                document=document
            )
            draft = revisions_qs.filter(status=DocumentRevision.Status.DRAFT).first()
            if draft:
                old_file = draft.file if draft.file else None
                draft.source = DocumentRevision.Source.UPLOADED
                draft.content = ""
                draft.file = upload
                draft.save()
                revision = draft
                # Only drop the previous blob once the swap is durably committed.
                if old_file:
                    transaction.on_commit(lambda f=old_file: f.delete(save=False))
            else:
                max_version = (
                    revisions_qs.aggregate(models.Max("version_number"))[
                        "version_number__max"
                    ]
                    or 0
                )
                revision = DocumentRevision.objects.create(
                    document=document,
                    version_number=max_version + 1,
                    source=DocumentRevision.Source.UPLOADED,
                    file=upload,
                    status=DocumentRevision.Status.DRAFT,
                    author=request.user,
                )
            # Don't repoint current_revision at an in-progress draft: it feeds the
            # reader and the container's status, which must stay on the published
            # revision (matches create-new-draft). Only set it for the first one.
            if document.current_revision_id is None:
                document.current_revision = revision
                document.save()
        return Response(
            {
                "id": str(revision.id),
                "version_number": revision.version_number,
                "status": revision.status,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="link-revision")
    def link_revision(self, request, pk=None):
        """Set an external URL as a new draft revision — or replace the current
        draft's URL. Follows the same review/publish lifecycle."""
        from django.core.validators import URLValidator

        document = self.get_object()
        url = (request.data.get("url") or "").strip()
        try:
            URLValidator(schemes=["http", "https"])(url)
        except DjangoValidationError:
            return Response(
                {"url": "Enter a valid http(s) URL."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            revisions_qs = DocumentRevision.objects.select_for_update().filter(
                document=document
            )
            draft = revisions_qs.filter(status=DocumentRevision.Status.DRAFT).first()
            if draft:
                old_file = draft.file if draft.file else None
                draft.source = DocumentRevision.Source.LINK
                draft.content = ""
                draft.file = None
                draft.url = url
                draft.save()
                revision = draft
                if old_file:
                    transaction.on_commit(lambda f=old_file: f.delete(save=False))
            else:
                max_version = (
                    revisions_qs.aggregate(models.Max("version_number"))[
                        "version_number__max"
                    ]
                    or 0
                )
                revision = DocumentRevision.objects.create(
                    document=document,
                    version_number=max_version + 1,
                    source=DocumentRevision.Source.LINK,
                    url=url,
                    status=DocumentRevision.Status.DRAFT,
                    author=request.user,
                )
            # Don't repoint current_revision at an in-progress draft: it feeds the
            # reader and the container's status, which must stay on the published
            # revision (matches create-new-draft). Only set it for the first one.
            if document.current_revision_id is None:
                document.current_revision = revision
                document.save()
        return Response(
            {
                "id": str(revision.id),
                "version_number": revision.version_number,
                "status": revision.status,
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentAttachmentViewSet(BaseModelViewSet):
    """
    API endpoint for serving document attachment files.
    """

    model = DocumentAttachment

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        """Serve the attachment file with correct content type."""
        try:
            pk_uuid = UUID(pk)
        except ValueError, AttributeError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        object_ids_view = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, DocumentAttachment
        )[0]
        if pk_uuid not in object_ids_view:
            return Response(status=status.HTTP_403_FORBIDDEN)
        attachment = self.get_object()
        if not attachment.file or not attachment.file.storage.exists(
            attachment.file.name
        ):
            return Response(status=status.HTTP_404_NOT_FOUND)
        SAFE_INLINE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
        guessed_type = (
            mimetypes.guess_type(attachment.file.name)[0] or "application/octet-stream"
        )
        # Only serve safe raster images inline; force download for anything else
        if guessed_type in SAFE_INLINE_TYPES:
            content_type = guessed_type
            disposition = "inline"
        else:
            content_type = "application/octet-stream"
            disposition = "attachment"
        filename = slugify(attachment.file.name.split("/")[-1].rsplit(".", 1)[0])
        extension = (
            attachment.file.name.rsplit(".", 1)[-1]
            if "." in attachment.file.name
            else ""
        )
        safe_filename = f"{filename}.{extension}" if extension else filename
        return HttpResponse(
            attachment.file,
            content_type=content_type,
            headers={
                "Content-Disposition": f'{disposition}; filename="{safe_filename}"'
            },
            status=status.HTTP_200_OK,
        )


class DocumentRevisionViewSet(BaseModelViewSet):
    """
    API endpoint that allows document revisions to be viewed or edited.
    """

    model = DocumentRevision
    filterset_fields = ["document", "status"]
    ordering = ["-version_number"]
    serializers_module = "doc_management.serializers"

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        """Serve an uploaded revision's file (PDF inline, everything else download)."""
        try:
            pk_uuid = UUID(pk)
        except ValueError, AttributeError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        object_ids_view = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, DocumentRevision
        )[0]
        if pk_uuid not in object_ids_view:
            return Response(status=status.HTTP_403_FORBIDDEN)
        revision = self.get_object()
        if not revision.file or not revision.file.storage.exists(revision.file.name):
            return Response(status=status.HTTP_404_NOT_FOUND)
        guessed_type = (
            mimetypes.guess_type(revision.file.name)[0] or "application/octet-stream"
        )
        is_pdf = guessed_type == "application/pdf"
        base = slugify(revision.file.name.split("/")[-1].rsplit(".", 1)[0])
        ext = revision.file.name.rsplit(".", 1)[-1] if "." in revision.file.name else ""
        safe_filename = f"{base}.{ext}" if ext else base
        return HttpResponse(
            revision.file,
            content_type="application/pdf" if is_pdf else "application/octet-stream",
            headers={
                "Content-Disposition": (
                    f"{'inline' if is_pdf else 'attachment'}; "
                    f'filename="{safe_filename}"'
                )
            },
            status=status.HTTP_200_OK,
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        # Payload edits are only allowed while a revision is being drafted.
        # Once it is submitted/validated/published, content is frozen — a new
        # version must go through `create-new-draft`. Guards against tampering
        # with an approved/published revision via a direct PATCH.
        if instance.status not in (
            DocumentRevision.Status.DRAFT,
            DocumentRevision.Status.CHANGE_REQUESTED,
        ):
            raise ValidationError(
                {
                    "__all__": "This revision is locked. Create a new draft to make changes."
                }
            )
        # Optimistic concurrency: check updated_at hasn't changed
        expected_updated_at = self.request.data.get("expected_updated_at")
        if expected_updated_at and instance.status == DocumentRevision.Status.DRAFT:
            from django.utils.dateparse import parse_datetime

            expected = parse_datetime(expected_updated_at)
            if expected and instance.updated_at > expected:
                editing_info = ""
                if instance.editing_user and instance.editing_user != self.request.user:
                    editing_info = f" by {instance.editing_user.email}"
                raise ValidationError(
                    {
                        "__all__": f"This revision has been modified{editing_info} since you loaded it. "
                        "Please reload and re-apply your changes."
                    }
                )
        old_content = instance.content
        instance = serializer.save()
        # Record edit history for draft revisions, only if content actually changed
        if (
            instance.status == DocumentRevision.Status.DRAFT
            and instance.content != old_content
        ):
            DocumentEdit.objects.create(
                revision=instance,
                editor=self.request.user,
                summary=instance.change_summary or "",
                content_snapshot=instance.content,
            )
            # Cap edit history to the 20 most recent entries per revision
            MAX_EDITS_PER_REVISION = 20
            edit_ids_to_keep = instance.edits.order_by("-created_at").values_list(
                "pk", flat=True
            )[:MAX_EDITS_PER_REVISION]
            instance.edits.exclude(pk__in=list(edit_ids_to_keep)).delete()

    @action(detail=True, methods=["post"], url_path="start-editing")
    def start_editing(self, request, pk=None):
        """Mark the current user as editing this revision.

        Uses select_for_update to prevent two concurrent requests from both
        believing they acquired the lock (race in the read-check-write path).
        """
        from django.db import transaction

        revision_id = self.get_object().pk
        now = timezone.now()

        with transaction.atomic():
            revision = DocumentRevision.objects.select_for_update().get(pk=revision_id)
            # Check if someone else holds the lock and it hasn't expired
            if (
                revision.editing_user_id
                and revision.editing_user_id != request.user.pk
                and revision.editing_since
                and (now - revision.editing_since).total_seconds() < 600
            ):
                return Response(
                    {
                        "locked": True,
                        "editing_user": {
                            "email": revision.editing_user.email,
                            "first_name": revision.editing_user.first_name,
                            "last_name": revision.editing_user.last_name,
                        },
                        "editing_since": revision.editing_since.isoformat(),
                    }
                )
            revision.editing_user = request.user
            revision.editing_since = now
            revision.save(update_fields=["editing_user", "editing_since"])
        return Response({"locked": False})

    @action(detail=True, methods=["post"], url_path="take-over-editing")
    def take_over_editing(self, request, pk=None):
        """Force-acquire the editing lock, overriding the current editor."""
        revision = self.get_object()
        revision.editing_user = request.user
        revision.editing_since = timezone.now()
        revision.save(update_fields=["editing_user", "editing_since"])
        return Response({"locked": False})

    @action(detail=True, methods=["post"], url_path="stop-editing")
    def stop_editing(self, request, pk=None):
        """Release the editing lock."""
        revision = self.get_object()
        if revision.editing_user == request.user:
            revision.editing_user = None
            revision.editing_since = None
            revision.save(update_fields=["editing_user", "editing_since"])
        return Response({"released": True})

    @action(detail=True, methods=["get"], url_path="editing-status")
    def editing_status(self, request, pk=None):
        """Check who is currently editing."""
        revision = self.get_object()
        if revision.editing_user and revision.editing_since:
            elapsed = (timezone.now() - revision.editing_since).total_seconds()
            if elapsed < 600:
                return Response(
                    {
                        "editing": True,
                        "is_me": revision.editing_user == request.user,
                        "editing_user": {
                            "email": revision.editing_user.email,
                            "first_name": revision.editing_user.first_name,
                            "last_name": revision.editing_user.last_name,
                        },
                        "editing_since": revision.editing_since.isoformat(),
                    }
                )
        return Response({"editing": False})

    @action(detail=True, methods=["get"], url_path="edit-history")
    def edit_history(self, request, pk=None):
        """Return the edit history for this revision."""
        revision = self.get_object()
        edits = revision.edits.select_related("editor").all()
        data = [
            {
                "id": str(edit.id),
                "editor": {
                    "id": str(edit.editor.id),
                    "email": edit.editor.email,
                    "first_name": edit.editor.first_name,
                    "last_name": edit.editor.last_name,
                }
                if edit.editor
                else None,
                "summary": edit.summary,
                "created_at": edit.created_at.isoformat(),
            }
            for edit in edits
        ]
        return Response(data)

    @action(
        detail=True,
        methods=["get"],
        url_path="edit-snapshot/(?P<edit_id>[^/.]+)",
    )
    def edit_snapshot(self, request, pk=None, edit_id=None):
        """Return the content snapshot of a specific edit."""
        revision = self.get_object()
        try:
            edit = revision.edits.get(pk=edit_id)
        except DocumentEdit.DoesNotExist:
            return Response(
                {"error": "Edit not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "id": str(edit.id),
                "content": edit.content_snapshot,
                "summary": edit.summary,
                "created_at": edit.created_at.isoformat(),
                "editor": {
                    "email": edit.editor.email,
                    "first_name": edit.editor.first_name,
                    "last_name": edit.editor.last_name,
                }
                if edit.editor
                else None,
            }
        )

    @action(detail=True, methods=["post"], url_path="submit-for-review")
    def submit_for_review(self, request, pk=None):
        """Transition from draft or change_requested to in_review."""
        revision = self.get_object()
        if revision.status not in (
            DocumentRevision.Status.DRAFT,
            DocumentRevision.Status.CHANGE_REQUESTED,
        ):
            return Response(
                {
                    "error": "Only draft or change-requested revisions can be submitted for review."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        revision.status = DocumentRevision.Status.IN_REVIEW
        revision.save()
        return Response({"status": "in_review"})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a revision: transition from in_review to validated."""
        revision = self.get_object()
        if revision.status != DocumentRevision.Status.IN_REVIEW:
            return Response(
                {"error": "Only in-review revisions can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        revision.validate(reviewer=request.user)
        return Response({"status": "validated"})

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish a validated revision: deprecate previous, generate PDF."""
        revision = self.get_object()
        if revision.status != DocumentRevision.Status.VALIDATED:
            return Response(
                {"error": "Only validated revisions can be published."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        revision.publish()

        # Uploaded revisions ARE the artifact (a file) — no markdown to snapshot.
        if revision.source == DocumentRevision.Source.AUTHORED:
            try:
                self._generate_pdf_snapshot(revision, request.user)
            except Exception as e:
                logger.warning("Failed to generate PDF snapshot", error=e)

        return Response({"status": "published"})

    @action(detail=True, methods=["post"], url_path="request-changes")
    def request_changes(self, request, pk=None):
        """Request changes on an in-review revision."""
        revision = self.get_object()
        if revision.status != DocumentRevision.Status.IN_REVIEW:
            return Response(
                {"error": "Only in-review revisions can have changes requested."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        revision.mark_change_requested(
            reviewer=request.user,
            comments=request.data.get("reviewer_comments", ""),
        )
        return Response({"status": "change_requested"})

    @action(
        detail=True,
        methods=["get"],
        url_path="diff/(?P<other_id>[^/.]+)",
    )
    def diff(self, request, pk=None, other_id=None):
        """Compute unified diff between this revision and another of the same document."""
        revision = self.get_object()
        try:
            other = revision.document.revisions.get(pk=other_id)
        except DocumentRevision.DoesNotExist:
            return Response(
                {"error": "Other revision not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        diff_lines = list(
            difflib.unified_diff(
                other.content.splitlines(keepends=True),
                revision.content.splitlines(keepends=True),
                fromfile=f"v{other.version_number}",
                tofile=f"v{revision.version_number}",
            )
        )
        return Response({"diff": "".join(diff_lines)})

    @action(
        detail=True,
        methods=["get"],
        url_path="edit-diff/(?P<edit_a_id>[^/.]+)/(?P<edit_b_id>[^/.]+)",
    )
    def edit_diff(self, request, pk=None, edit_a_id=None, edit_b_id=None):
        """Compute unified diff between two DocumentEdit content snapshots."""
        revision = self.get_object()
        try:
            edit_a = revision.edits.select_related("editor").get(pk=edit_a_id)
        except DocumentEdit.DoesNotExist:
            return Response(
                {"error": "Edit A not found in this revision."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            edit_b = revision.edits.select_related("editor").get(pk=edit_b_id)
        except DocumentEdit.DoesNotExist:
            return Response(
                {"error": "Edit B not found in this revision."},
                status=status.HTTP_404_NOT_FOUND,
            )

        def _edit_info(edit):
            return {
                "id": str(edit.id),
                "editor": {
                    "email": edit.editor.email,
                    "first_name": edit.editor.first_name,
                    "last_name": edit.editor.last_name,
                }
                if edit.editor
                else None,
                "created_at": edit.created_at.isoformat(),
                "summary": edit.summary,
            }

        diff_lines = list(
            difflib.unified_diff(
                edit_a.content_snapshot.splitlines(keepends=True),
                edit_b.content_snapshot.splitlines(keepends=True),
                fromfile=f"Edit by {edit_a.editor.email if edit_a.editor else 'unknown'}",
                tofile=f"Edit by {edit_b.editor.email if edit_b.editor else 'unknown'}",
            )
        )
        return Response(
            {
                "diff": "".join(diff_lines),
                "from_edit": _edit_info(edit_a),
                "to_edit": _edit_info(edit_b),
            }
        )

    @staticmethod
    def _inline_images(html_content, accessible_ids):
        """Replace document attachment image URLs with base64 data URIs for PDF export."""
        import base64
        import re

        def replace_match(match):
            attachment_id = match.group(1)
            if UUID(attachment_id) not in accessible_ids:
                return match.group(0)
            try:
                attachment = DocumentAttachment.objects.get(pk=attachment_id)
                if attachment.file and attachment.file.storage.exists(
                    attachment.file.name
                ):
                    file_data = attachment.file.read()
                    content_type = (
                        mimetypes.guess_type(attachment.file.name)[0]
                        or "application/octet-stream"
                    )
                    b64 = base64.b64encode(file_data).decode("ascii")
                    return f'src="data:{content_type};base64,{b64}"'
            except DocumentAttachment.DoesNotExist:
                pass
            return match.group(0)

        # Match src attributes pointing to serve-image with a UUID attachment_id
        UUID_RE = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        return re.sub(
            r'src="[^"]*[?&]_action=serve-image&amp;attachment_id=(' + UUID_RE + r')"',
            replace_match,
            html_content,
        )

    @action(detail=True, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request, pk=None):
        """Export revision content as a PDF document."""
        revision = self.get_object()
        pdf = self._render_pdf_bytes(revision, request.user)
        response = HttpResponse(pdf, content_type="application/pdf")
        filename = slugify(revision.document.display_name)
        response["Content-Disposition"] = (
            f'attachment; filename="{filename}_v{revision.version_number}.pdf"'
        )
        return response

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(DocumentRevision.Status.choices))

    def _render_pdf_bytes(self, revision, user):
        """Render a revision to PDF bytes (shared by export and snapshot)."""
        import markdown as md_lib
        from django.utils.safestring import mark_safe

        content_html = md_lib.markdown(
            revision.content,
            extensions=["tables", "fenced_code", "toc", "nl2br"],
        )
        accessible_ids = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), user, DocumentAttachment
        )[0]
        content_html = mark_safe(self._inline_images(content_html, set(accessible_ids)))
        author_name = ""
        if revision.author:
            author_name = (
                f"{revision.author.first_name} {revision.author.last_name}".strip()
                or revision.author.email
            )
        doc = revision.document
        container = getattr(doc, "container", None)
        document_type_label = ""
        if container:
            document_type_label = dict(container.DocumentType.choices).get(
                container.document_type, container.document_type
            )
        logo_base64, logo_mime_type = self._client_logo()
        cls = getattr(container, "classification", None) if container else None
        classification = (
            {
                "abbreviation": cls.abbreviation,
                "name": cls.name,
                "hexcolor": cls.hexcolor or "#000000",
                "scheme": cls.object_classification.ref_id
                or cls.object_classification.name,
            }
            if cls
            else None
        )
        context = {
            "policy_name": doc.display_name,
            "classification": classification,
            "version_number": revision.version_number,
            "status": revision.status,
            "status_display": revision.get_status_display(),
            "author_name": author_name,
            "published_at": (
                revision.published_at.strftime("%Y-%m-%d")
                if revision.published_at
                else ""
            ),
            "date": timezone.now().strftime("%Y-%m-%d"),
            "content_html": content_html,
            # Aliases exposed to custom override templates (DOC_HTML_TEMPLATE_REGISTRY).
            "title": doc.display_name,
            "content": content_html,
            "version": revision.version_number,
            "document_type": document_type_label,
            "logo_base64": logo_base64,
            "logo_mime_type": logo_mime_type,
        }
        html_string = self._resolve_document_html(revision, context)

        return HTML(string=html_string, url_fetcher=_safe_url_fetcher).write_pdf()

    def _client_logo(self):
        """Return (base64, mime_type) of the org logo, or ('', '') in the
        community edition where ClientSettings is not installed."""
        try:
            from enterprise_core.models import ClientSettings
        except Exception:
            return "", ""
        cs = ClientSettings.objects.first()
        if not cs or not cs.logo:
            return "", ""
        return cs.logo_base64 or "", cs.logo_mime_type or ""

    def _resolve_document_html(self, revision, context):
        """Render the document PDF HTML, preferring an active per-language
        custom override (enterprise) over the built-in template."""
        from core.models import CustomDocHtmlTemplate
        from django.template import Template, Context
        from .html_templates import find_forbidden_template_tags

        locale = getattr(revision.document, "locale", None) or "en"
        override = (
            CustomDocHtmlTemplate.objects.filter(
                template_key="document_pdf", language=locale, is_active=True
            )
            .exclude(file="")
            .first()
        )
        if override and override.file:
            try:
                with override.file.open("rb") as fh:
                    template_source = fh.read().decode("utf-8")
                forbidden = find_forbidden_template_tags(template_source)
                if forbidden:
                    logger.warning(
                        "Custom document template uses forbidden tags, falling back",
                        tags=forbidden,
                    )
                else:
                    return Template(template_source).render(Context(context))
            except Exception as e:
                logger.warning(
                    "Failed to render custom document template, falling back to default",
                    error=e,
                )
        return render_to_string("doc_management/policy_document_pdf.html", context)

    def _generate_pdf_snapshot(self, revision, user):
        """Generate and save a PDF snapshot for a revision."""
        from django.core.files.base import ContentFile

        pdf_content = self._render_pdf_bytes(revision, user)
        filename = slugify(revision.document.display_name)
        revision.pdf_snapshot.save(
            f"{filename}_v{revision.version_number}.pdf",
            ContentFile(pdf_content),
            save=True,
        )
