from rest_framework import serializers

from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer

from .models import FrameworkSnapshot, Portal, PortalPreset, PublicDocument


class PortalPresetReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    is_user_authored = serializers.SerializerMethodField()

    class Meta:
        model = PortalPreset
        fields = [
            "id",
            "name",
            "description",
            "urn",
            "ref_id",
            "version",
            "provider",
            "translations",
            "content",
            "folder",
            "is_user_authored",
            "created_at",
            "updated_at",
        ]

    def get_is_user_authored(self, obj) -> bool:
        return obj.urn is None


class PortalPresetWriteSerializer(BaseModelSerializer):
    class Meta:
        model = PortalPreset
        fields = ["name", "description", "folder", "translations", "content"]


class PortalReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    audience_groups = FieldsRelatedField(many=True)

    class Meta:
        model = Portal
        fields = "__all__"


class PortalWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Portal
        fields = [
            "id",
            "name",
            "description",
            "folder",
            "status",
            "enabled",
            "is_public",
            "audience_groups",
            "is_default",
            "is_primary",
            "order",
            "branding",
            "content",
            "source_ref",
        ]

    def validate_branding(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("must be an object")
        return value

    def validate_content(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("must be an object")
        if not isinstance(value.get("sections", []), list):
            raise serializers.ValidationError("sections must be a list")
        return value


class FrameworkSnapshotReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    source_audit = FieldsRelatedField()
    control_count = serializers.SerializerMethodField()

    class Meta:
        model = FrameworkSnapshot
        fields = [
            "id",
            "name",
            "description",
            "folder",
            "source_audit",
            "implementation_groups",
            "framework_name",
            "framework_ref_id",
            "framework_version",
            "synced_at",
            "summary",
            "content",
            "control_count",
            "public_token",
            "created_at",
            "updated_at",
        ]

    def get_control_count(self, obj) -> int:
        return len(obj.control_ids or [])


class FrameworkSnapshotWriteSerializer(BaseModelSerializer):
    class Meta:
        model = FrameworkSnapshot
        fields = [
            "name",
            "description",
            "folder",
            "source_audit",
            "implementation_groups",
        ]


class PublicDocumentReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()

    class Meta:
        model = PublicDocument
        fields = [
            "id",
            "name",
            "description",
            "folder",
            "token",
            "mime_type",
            "size",
            "created_at",
            "updated_at",
        ]


class PublicDocumentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = PublicDocument
        fields = ["name", "description", "folder", "file"]

    def _apply_file_meta(self, validated_data):
        f = validated_data.get("file")
        if f is not None:
            validated_data["size"] = getattr(f, "size", 0) or 0
            validated_data["mime_type"] = getattr(f, "content_type", "") or ""

    def create(self, validated_data):
        self._apply_file_meta(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._apply_file_meta(validated_data)
        return super().update(instance, validated_data)
