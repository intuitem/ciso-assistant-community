from core.serializers import (
    BaseModelSerializer,
    ReferentialSerializer,
    FieldsRelatedField,
    PathField,
)
from .models import CVE, CWE


class CVEWriteSerializer(BaseModelSerializer):
    class Meta:
        model = CVE
        exclude = ["translations"]


class CVEReadSerializer(ReferentialSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)

    class Meta:
        model = CVE
        exclude = ["translations"]


class CWEWriteSerializer(BaseModelSerializer):
    class Meta:
        model = CWE
        exclude = ["translations"]


class CWEReadSerializer(ReferentialSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)

    class Meta:
        model = CWE
        exclude = ["translations"]
