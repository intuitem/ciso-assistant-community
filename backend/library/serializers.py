from core.models import StoredLibrary, LoadedLibrary
from rest_framework import serializers
from core.serializers import ReferentialSerializer

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
            "builtin",
            "objects_meta",
            "is_loaded",
        ]


class StoredLibraryDetailedSerializer(ReferentialSerializer):
    class Meta:
        model = StoredLibrary
        exclude = ["translations"]


class LoadedLibraryDetailedSerializer(ReferentialSerializer):
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
    id = serializers.CharField()
    locale = serializers.ChoiceField(choices=["en", "fr"])
    # objects = LibraryObjectSerializer(many=True)
    version = serializers.CharField()
    copyright = serializers.CharField()
    builtin = serializers.BooleanField()


"""class LibraryModelSerializer(BaseModelSerializer):
    class Meta:
        model = LoadedLibrary
        fields = "__all__"
"""


class LibraryUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    class Meta:
        fields = ["file"]
