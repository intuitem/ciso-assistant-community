from pathlib import Path

from django.db import models
from rest_framework import serializers

from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer

from .models import DocumentRevision, ManagedDocument


class ManagedDocumentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ManagedDocument
        fields = "__all__"

    def _resolve_template_path(self, template_name, request):
        """Find the template file in the user's preferred language, falling back to 'en'."""
        base_dir = (
            Path(__file__).resolve().parent.parent / "library" / "policy_templates"
        )
        lang = "en"
        if (
            request
            and hasattr(request, "user")
            and hasattr(request.user, "get_preferences")
        ):
            lang = request.user.get_preferences().get("lang", "en")
        for try_lang in [lang, "en"]:
            path = base_dir / try_lang / f"{template_name}.md"
            if path.exists():
                return path
        return None

    def create(self, validated_data):
        document = super().create(validated_data)
        # Auto-create an initial draft revision
        request = self.context.get("request")
        author = request.user if request else None
        content = ""
        if template_name := validated_data.get("template_used"):
            template_path = self._resolve_template_path(template_name, request)
            if template_path:
                raw = template_path.read_text(encoding="utf-8")
                # Strip YAML frontmatter
                if raw.startswith("---"):
                    parts = raw.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()
                    else:
                        content = raw
                else:
                    content = raw
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

    def create(self, validated_data):
        document = validated_data["document"]
        max_version = DocumentRevision.objects.filter(document=document).aggregate(
            models.Max("version_number")
        )["version_number__max"]
        validated_data["version_number"] = (max_version or 0) + 1
        request = self.context.get("request")
        if request and not validated_data.get("author"):
            validated_data["author"] = request.user
        return super().create(validated_data)


class DocumentRevisionReadSerializer(BaseModelSerializer):
    document = FieldsRelatedField()
    author = FieldsRelatedField(fields=["id", "email", "first_name", "last_name"])
    reviewer = FieldsRelatedField(fields=["id", "email", "first_name", "last_name"])
    status_display = serializers.CharField(source="get_status_display")

    class Meta:
        model = DocumentRevision
        fields = "__all__"
