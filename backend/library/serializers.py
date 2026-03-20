from typing import Optional

from rest_framework import serializers

from core.models import LoadedLibrary, StoredLibrary
from core.serializer_fields import FieldsRelatedField, HashSlugRelatedField
from core.serializers import BaseModelSerializer, ReferentialSerializer


class StoredLibrarySerializer(ReferentialSerializer):
    locales = serializers.ListField(source="get_locales", read_only=True)
    loaded_library = serializers.SerializerMethodField()
    filtering_labels = FieldsRelatedField(many=True, fields=["id", "label"])
    is_preset = serializers.BooleanField(read_only=True)
    profile = serializers.SerializerMethodField()
    scaffolded_objects = serializers.SerializerMethodField()

    def get_loaded_library(self, obj) -> Optional[str]:
        loaded_library = obj.get_loaded_library()
        return str(loaded_library.id) if loaded_library else None

    def get_profile(self, obj) -> Optional[dict]:
        if obj.is_preset:
            return obj.content.get("preset", {}).get("profile")
        return None

    def get_scaffolded_objects(self, obj) -> Optional[list]:
        if not obj.is_preset:
            return None
        items = obj.content.get("preset", {}).get("scaffolded_objects", [])
        if not items:
            return None
        from collections import Counter

        counts = Counter(item["type"] for item in items)
        return [
            {"type": obj_type, "count": count} for obj_type, count in counts.items()
        ]

    class Meta:
        model = StoredLibrary
        fields = [
            "id",
            "name",
            "description",
            "urn",
            "ref_id",
            "locale",
            "version",
            "packager",
            "provider",
            "filtering_labels",
            "publication_date",
            "builtin",
            "objects_meta",
            "reference_count",
            "is_loaded",
            "is_update",
            "locales",
            "loaded_library",
            "copyright",
            "is_preset",
            "profile",
            "scaffolded_objects",
        ]


class StoredLibraryDetailedSerializer(ReferentialSerializer):
    locales = serializers.ListField(source="get_locales", read_only=True)

    class Meta:
        model = StoredLibrary
        exclude = ["translations"]


class LoadedLibraryImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    dependencies = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)

    class Meta:
        model = LoadedLibrary
        fields = [
            "created_at",
            "updated_at",
            "version",
            "folder",
            "urn",
            "ref_id",
            "provider",
            "name",
            "description",
            "annotation",
            "locale",
            "packager",
            "publication_date",
            "builtin",
            "objects_meta",
            "translations",
            "dependencies",
            "copyright",
        ]


class LoadedLibraryDetailedSerializer(ReferentialSerializer):
    locales = serializers.ListField(source="get_locales", read_only=True)
    dependencies = FieldsRelatedField(many=True, fields=["id", "urn", "str", "name"])

    class Meta:
        model = LoadedLibrary
        exclude = ["translations"]


class LoadedLibrarySerializer(ReferentialSerializer):
    locales = serializers.ListField(source="get_locales", read_only=True)

    class Meta:
        model = LoadedLibrary
        fields = [
            "id",
            "name",
            "description",
            "urn",
            "ref_id",
            "locale",
            "version",
            "packager",
            "provider",
            "publication_date",
            "builtin",
            "objects_meta",
            "reference_count",
            "locales",
            "has_update",
        ]


class LibraryUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    class Meta:
        fields = ["file"]
