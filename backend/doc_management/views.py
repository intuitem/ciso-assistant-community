import difflib
import mimetypes
from pathlib import Path
from uuid import UUID

import structlog
import yaml
from django.db import models
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

from core.views import BaseModelViewSet
from iam.models import RoleAssignment, Folder

from .models import DocumentAttachment, DocumentEdit, DocumentRevision, ManagedDocument

logger = structlog.get_logger(__name__)

TEMPLATES_BASE_DIR = (
    Path(__file__).resolve().parent.parent / "library" / "policy_templates"
)


def _get_user_lang(request):
    """Get the user's preferred language from their preferences."""
    if hasattr(request, "user") and hasattr(request.user, "get_preferences"):
        return request.user.get_preferences().get("lang", "en")
    return "en"


def _get_templates_dir(lang: str) -> Path:
    """Resolve the templates directory for the given language, falling back to 'en'."""
    localized = TEMPLATES_BASE_DIR / lang
    if localized.exists() and any(localized.glob("*.md")):
        return localized
    return TEMPLATES_BASE_DIR / "en"


class ManagedDocumentViewSet(BaseModelViewSet):
    """
    API endpoint that allows managed documents to be viewed or edited.
    """

    model = ManagedDocument
    filterset_fields = ["policy", "folder", "document_type", "locale"]
    serializers_module = "doc_management.serializers"

    @action(detail=False, methods=["get"])
    def templates(self, request):
        """List available document templates in the user's preferred language."""
        lang = _get_user_lang(request)
        template_dir = _get_templates_dir(lang)
        templates = []
        if template_dir.exists():
            for f in sorted(template_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                metadata = {
                    "id": f.stem,
                    "title": f.stem.replace("_", " ").title(),
                    "lang": template_dir.name,
                }
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        try:
                            fm = yaml.safe_load(parts[1])
                            if isinstance(fm, dict):
                                metadata.update(fm)
                        except yaml.YAMLError:
                            pass
                templates.append(metadata)
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
        except (ValueError, AttributeError):
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

    def perform_update(self, serializer):
        instance = self.get_object()
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
        """Approve a revision: set published, deprecate previous, generate PDF."""
        revision = self.get_object()
        if revision.status != DocumentRevision.Status.IN_REVIEW:
            return Response(
                {"error": "Only in-review revisions can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        revision.publish(reviewer=request.user)

        # Generate PDF snapshot
        try:
            self._generate_pdf_snapshot(revision)
        except Exception as e:
            logger.warning("Failed to generate PDF snapshot", error=str(e))

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
    def _inline_images(html_content):
        """Replace document attachment image URLs with base64 data URIs for PDF export."""
        import base64
        import re

        def replace_match(match):
            attachment_id = match.group(1)
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
        pdf = self._render_pdf_bytes(revision)
        response = HttpResponse(pdf, content_type="application/pdf")
        filename = slugify(revision.document.display_name)
        response["Content-Disposition"] = (
            f'attachment; filename="{filename}_v{revision.version_number}.pdf"'
        )
        return response

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(DocumentRevision.Status.choices))

    def _render_pdf_bytes(self, revision):
        """Render a revision to PDF bytes (shared by export and snapshot)."""
        import markdown as md_lib

        content_html = md_lib.markdown(
            revision.content,
            extensions=["tables", "fenced_code", "toc", "nl2br"],
        )
        content_html = self._inline_images(content_html)
        author_name = ""
        if revision.author:
            author_name = (
                f"{revision.author.first_name} {revision.author.last_name}".strip()
                or revision.author.email
            )
        context = {
            "policy_name": revision.document.display_name,
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
        }
        html_string = render_to_string(
            "doc_management/policy_document_pdf.html", context
        )

        def _safe_url_fetcher(url, timeout=10, ssl_context=None):
            """Allow data URIs and public HTTPS images, block everything else.

            Prevents SSRF via file://, internal network URLs, or non-HTTPS schemes
            while still allowing users to embed external logos/images.
            """
            if url.startswith("data:"):
                return weasyprint.default_url_fetcher(url)
            if url.startswith("https://"):
                return weasyprint.default_url_fetcher(
                    url, timeout=timeout, ssl_context=ssl_context
                )
            raise ValueError(f"Blocked resource loading for URL scheme: {url}")

        return HTML(string=html_string, url_fetcher=_safe_url_fetcher).write_pdf()

    def _generate_pdf_snapshot(self, revision):
        """Generate and save a PDF snapshot for a revision."""
        from django.core.files.base import ContentFile

        pdf_content = self._render_pdf_bytes(revision)
        filename = slugify(revision.document.display_name)
        revision.pdf_snapshot.save(
            f"{filename}_v{revision.version_number}.pdf",
            ContentFile(pdf_content),
            save=True,
        )
