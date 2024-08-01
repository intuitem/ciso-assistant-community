from core.serializers import BaseModelSerializer
from iam.models import Folder


class FolderWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Folder
        exclude = [
            "builtin",
            "content_type",
        ]
