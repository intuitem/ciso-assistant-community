from rest_framework import serializers

from core.models import LoadedLibrary, StoredLibrary
from core.serializer_fields import FieldsRelatedField, HashSlugRelatedField
from core.serializers import BaseModelSerializer, ReferentialSerializer


class StoredLibrarySerializer(ReferentialSerializer):
    locales = serializers.ListField(source="get_locales", read_only=True)

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
            "publication_date",
            "builtin",
            "objects_meta",
            "is_loaded",
            "locales",
            "copyright",
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
    dependencies = FieldsRelatedField(many=True, fields=["urn", "str", "name"])

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
