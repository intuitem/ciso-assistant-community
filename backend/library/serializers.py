from core.models import StoredLibrary, LoadedLibrary
from core.serializers import (
    BaseModelSerializer,
)
from rest_framework import serializers

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

class StoredLibrarySerializer(serializers.ModelSerializer):
    # Not used yet
    class Meta:
        model = StoredLibrary
        fields = ["id","name","description","locale","version","builtin","objects_meta"]

    # name = serializers.CharField()
    # description = serializers.CharField()
    # locale = serializers.ChoiceField(choices=["en", "fr"])
    # version = serializers.CharField()
    # copyright = serializers.CharField()
    # builtin = serializers.BooleanField()
    # objects_meta = serializers.JSONField()

class StoredLibraryDetailedSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredLibrary
        fields = "__all__"

"""
class StoredLibraryReadSerializer(StoredLibraryWriteSerializer):
    content = serializers.SerializerMethodField()

    def get_content(self, content: bytes):
        return content.encode("utf-8") # Should we enforce UTF-8 for library files ?
"""

class LoadedLibrarySerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
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
