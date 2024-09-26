from rest_framework import serializers
from core.serializers import BaseModelSerializer
from iam.models import Folder

from .models import ClientSettings


class FolderWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Folder
        exclude = [
            "builtin",
            "content_type",
        ]


class ClientSettingsWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ClientSettings
        exclude = ["is_published", "folder"]


class ClientSettingsReadSerializer(BaseModelSerializer):
    logo_hash = serializers.CharField()
    favicon_hash = serializers.CharField()

    class Meta:
        model = ClientSettings
        exclude = ["is_published", "folder"]
