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
    class Meta:
        model = ClientSettings
        exclude = ["is_published", "folder"]

    def update(self, instance, validated_data):
        instance = self.instance
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance
