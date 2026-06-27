import re

from django.contrib.auth.models import Permission
from rest_framework import serializers

from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer
from iam.models import Folder, RoleAssignment

from .models import FrameworkSnapshot, Portal, PortalPreset, PublicDocument

# accent_color goes verbatim into an inline style on the public trust page; constrain it.
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$|^rgba?\(", re.IGNORECASE)


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
        accent = value.get("accent_color")
        if accent not in (None, "") and not _COLOR_RE.match(str(accent)):
            raise serializers.ValidationError(
                {"accent_color": "must be a hex or rgb()/rgba() color"}
            )
        logo = value.get("logo_url")
        if logo not in (None, "") and not str(logo).startswith(("http://", "https://")):
            raise serializers.ValidationError({"logo_url": "must be an http(s) URL"})
        tagline = value.get("tagline")
        if tagline is not None and len(str(tagline)) > 280:
            raise serializers.ValidationError(
                {"tagline": "must be at most 280 characters"}
            )
        return value

    def validate_content(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("must be an object")
        sections = value.get("sections", [])
        if not isinstance(sections, list):
            raise serializers.ValidationError("sections must be a list")
        for section in sections:
            if not isinstance(section, dict):
                raise serializers.ValidationError("each section must be an object")
            items = section.get("items", [])
            if not isinstance(items, list) or any(
                not isinstance(i, dict) for i in items
            ):
                raise serializers.ValidationError("section items must be objects")
        return value

    def validate(self, data):
        # Claiming the single global primary trust-center URL is an instance-wide effect,
        # so it takes settings-level rights — not just folder-scoped change_portal.
        if data.get("is_primary"):
            request = self.context.get("request")
            allowed = request is not None and RoleAssignment.is_access_allowed(
                user=request.user,
                perm=Permission.objects.get(codename="change_globalsettings"),
                folder=Folder.get_root_folder(),
            )
            if not allowed:
                raise serializers.ValidationError(
                    {"is_primary": "Only an administrator can set the primary portal."}
                )
        return super().validate(data)


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
            "display_mode",
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
            "display_mode",
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
        # id + token are read-only (pk / editable=False) — surfaced so the create
        # response can hand back the token for inline linking.
        fields = ["id", "name", "description", "folder", "file", "token"]

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
