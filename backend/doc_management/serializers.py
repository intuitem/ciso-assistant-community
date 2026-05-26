from uuid import UUID

from django.db import models, transaction
from rest_framework import serializers

from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer
from iam.models import Folder, RoleAssignment

from .models import DocumentRevision, DocumentTemplate, ManagedDocument


class ManagedDocumentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ManagedDocument
        fields = "__all__"

    def _resolve_template(self, template_ref, locale, request):
        """Resolve template_used to a DocumentTemplate row, IAM-scoped.

        Accepts either a UUID (preferred) or a ref_id (e.g. 'access_control')
        for backward compatibility with the previous filesystem-based shorthand.
        """
        qs = DocumentTemplate.objects.all()
        if request and hasattr(request, "user"):
            accessible_ids = RoleAssignment.get_accessible_object_ids(
                Folder.get_root_folder(), request.user, DocumentTemplate
            )[0]
            qs = qs.filter(pk__in=accessible_ids)
        try:
            return qs.filter(pk=UUID(str(template_ref))).first()
        except (ValueError, TypeError, AttributeError):
            pass
        return qs.filter(ref_id=template_ref, locale=locale).first()

    def create(self, validated_data):
        # Default locale to user's preferred language
        request = self.context.get("request")
        if "locale" not in validated_data or not validated_data.get("locale"):
            lang = "en"
            if (
                request
                and hasattr(request, "user")
                and hasattr(request.user, "get_preferences")
            ):
                lang = request.user.get_preferences().get("lang", "en")
            validated_data["locale"] = lang

        # Auto-create an initial draft revision atomically with the document
        author = request.user if request else None
        content = ""
        if template_ref := validated_data.get("template_used"):
            template_obj = self._resolve_template(
                template_ref, validated_data.get("locale", "en"), request
            )
            if template_obj is not None:
                content = template_obj.content
        with transaction.atomic():
            # Set default_locale inside the transaction to avoid race conditions
            # where two concurrent creates both see no siblings and both set True
            policy = validated_data.get("policy")
            if policy:
                has_siblings = (
                    ManagedDocument.objects.select_for_update()
                    .filter(policy=policy)
                    .exists()
                )
                validated_data.setdefault("default_locale", not has_siblings)
            else:
                validated_data.setdefault("default_locale", True)

            document = super().create(validated_data)
            revision = DocumentRevision.objects.create(
                document=document,
                version_number=1,
                content=content,
                author=author,
            )
            document.current_revision = revision
            document.save()
        return document


class ManagedDocumentReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    policy = FieldsRelatedField()
    current_revision = FieldsRelatedField(
        fields=["id", "version_number", "status", "published_at", "author"],
    )
    revision_count = serializers.SerializerMethodField()
    latest_draft = serializers.SerializerMethodField()
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = ManagedDocument
        fields = "__all__"

    def get_revision_count(self, obj):
        return obj.revisions.count()

    def get_latest_draft(self, obj):
        draft = obj.revisions.filter(status=DocumentRevision.Status.DRAFT).first()
        return str(draft.id) if draft else None


class DocumentRevisionWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DocumentRevision
        fields = "__all__"
        # Workflow fields are managed exclusively by dedicated actions
        # (submit-for-review, approve, request-changes, start-editing, etc.)
        # and model methods — not directly writable via PATCH.
        read_only_fields = [
            "status",
            "reviewer",
            "reviewer_comments",
            "published_at",
            "pdf_snapshot",
            "editing_user",
            "editing_since",
            "version_number",
            "author",
        ]

    def create(self, validated_data):
        document = validated_data["document"]
        request = self.context.get("request")
        if request and not validated_data.get("author"):
            validated_data["author"] = request.user
        with transaction.atomic():
            # Lock existing revisions to prevent concurrent version_number collisions
            max_version = (
                DocumentRevision.objects.select_for_update()
                .filter(document=document)
                .aggregate(models.Max("version_number"))["version_number__max"]
            )
            validated_data["version_number"] = (max_version or 0) + 1
            return super().create(validated_data)


class DocumentRevisionReadSerializer(BaseModelSerializer):
    document = FieldsRelatedField()
    author = FieldsRelatedField(fields=["id", "email", "first_name", "last_name"])
    reviewer = FieldsRelatedField(fields=["id", "email", "first_name", "last_name"])
    status_display = serializers.CharField(source="get_status_display")

    class Meta:
        model = DocumentRevision
        fields = "__all__"


class DocumentTemplateWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DocumentTemplate
        fields = "__all__"
        # origin is server-controlled: set by startup seed for built-ins,
        # implicit default (USER) for everything else.
        read_only_fields = ["origin"]

    BUILTIN_MUTABLE_FIELDS = {"status"}

    def update(self, instance, validated_data):
        if instance.origin == DocumentTemplate.Origin.BUILTIN:
            forbidden = set(validated_data.keys()) - self.BUILTIN_MUTABLE_FIELDS
            if forbidden:
                raise serializers.ValidationError(
                    {
                        field: "This field cannot be edited on a built-in template. Duplicate it first to customize."
                        for field in forbidden
                    }
                )
        return super().update(instance, validated_data)


class DocumentTemplateReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    document_type_display = serializers.CharField(source="get_document_type_display")
    status_display = serializers.CharField(source="get_status_display")
    origin_display = serializers.CharField(source="get_origin_display")

    class Meta:
        model = DocumentTemplate
        fields = "__all__"
