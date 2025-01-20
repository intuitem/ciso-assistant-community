from core.models import StoredLibrary, LoadedLibrary
from rest_framework import serializers
from core.serializers import ReferentialSerializer, BaseModelSerializer
from core.serializer_fields import FieldsRelatedField, HashSlugRelatedField

"""class LibraryObjectSerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=[
            "risk_matrix",
            "reference_control",
            "threat",
            "framework",
        ]
    )
    fields = serializers.DictField(child=serializers.CharField())
"""


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


"""
class StoredLibraryReadSerializer(StoredLibraryWriteSerializer):
    content = serializers.SerializerMethodField()

    def get_content(self, content: bytes):
        return content.encode("utf-8") # Should we enforce UTF-8 for library files ?
"""


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
        ]


"""class LibraryModelSerializer(BaseModelSerializer):
    class Meta:
        model = LoadedLibrary
        fields = "__all__"
"""


class LibraryUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    class Meta:
        fields = ["file"]
