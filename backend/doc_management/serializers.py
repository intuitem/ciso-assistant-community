from django.db import models, transaction
from rest_framework import serializers

from core.models import Policy
from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer

from .models import (
    DocumentContainer,
    DocumentRevision,
    DocumentTemplate,
    ManagedDocument,
)


class DocumentContainerReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    policies = FieldsRelatedField(many=True)
    applied_controls = FieldsRelatedField(many=True)
    task_templates = FieldsRelatedField(many=True)
    processings = FieldsRelatedField(many=True)
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentContainer
        fields = "__all__"

    def get_document_count(self, obj):
        return obj.documents.count()


class DocumentContainerWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DocumentContainer
        fields = "__all__"


class ManagedDocumentWriteSerializer(BaseModelSerializer):
    # Write-only inputs that resolve/seed the container; not model fields (the
    # legacy policy/document_type columns were dropped in the Stream A contract).
    policy = serializers.PrimaryKeyRelatedField(
        queryset=Policy.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    document_type = serializers.ChoiceField(
        choices=DocumentContainer.DocumentType.choices,
        required=False,
        write_only=True,
    )

    class Meta:
        model = ManagedDocument
        fields = "__all__"

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

        # Container inputs (write-only, not model fields).
        policy = validated_data.pop("policy", None)
        document_type = (
            validated_data.pop("document_type", None)
            or DocumentContainer.DocumentType.POLICY
        )

        # Auto-create an initial draft revision atomically with the document
        author = request.user if request else None
        content = ""
        if template_name := validated_data.get("template_used"):
            locale = validated_data.get("locale", "en")
            template = (
                DocumentTemplate.objects.filter(
                    ref_id=template_name, locale=locale
                ).first()
                or DocumentTemplate.objects.filter(
                    ref_id=template_name, locale="en"
                ).first()
            )
            if template:
                content = template.content
        with transaction.atomic():
            # Resolve the container that groups this document's locale variants.
            # Legacy/policy flow: one container per policy. Standalone: a fresh one.
            container = validated_data.get("container")
            if container is None:
                if policy is not None:
                    container = (
                        DocumentContainer.objects.select_for_update()
                        .filter(policies=policy)
                        .first()
                    )
                    if container is None:
                        container = DocumentContainer.objects.create(
                            document_type=document_type,
                            name=validated_data.get("name")
                            or getattr(policy, "name", ""),
                            folder=policy.folder,
                            is_published=policy.is_published,
                        )
                        container.policies.add(policy)
                else:
                    container = DocumentContainer.objects.create(
                        document_type=document_type,
                        name=validated_data.get("name", ""),
                        is_published=False,
                        **(
                            {"folder": validated_data["folder"]}
                            if validated_data.get("folder")
                            else {}
                        ),
                    )
                validated_data["container"] = container

            # Set default_locale inside the transaction to avoid race conditions
            # where two concurrent creates both see no siblings and both set True
            has_siblings = (
                ManagedDocument.objects.select_for_update()
                .filter(container=container)
                .exists()
            )
            validated_data.setdefault("default_locale", not has_siblings)

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
    container = FieldsRelatedField()
    current_revision = FieldsRelatedField(
        fields=["id", "version_number", "status", "published_at", "author"],
    )
    revision_count = serializers.SerializerMethodField()
    latest_draft = serializers.SerializerMethodField()
    display_name = serializers.CharField(read_only=True)
    document_type = serializers.SerializerMethodField()

    class Meta:
        model = ManagedDocument
        fields = "__all__"

    def get_document_type(self, obj):
        return obj.container.document_type if obj.container_id else None

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
