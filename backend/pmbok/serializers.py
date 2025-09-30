from rest_framework import serializers

from core.serializers import BaseModelSerializer
from core.serializer_fields import FieldsRelatedField, PathField
from pmbok.models import GenericCollection, Accreditation


class GenericCollectionReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    compliance_assessments = FieldsRelatedField(many=True)
    risk_assessments = FieldsRelatedField(many=True)
    crq_studies = FieldsRelatedField(many=True)
    ebios_studies = FieldsRelatedField(many=True)
    entity_assessments = FieldsRelatedField(many=True)
    documents = FieldsRelatedField(many=True)
    dependencies = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(["folder"], many=True)

    class Meta:
        model = GenericCollection
        fields = "__all__"


class GenericCollectionWriteSerializer(BaseModelSerializer):
    class Meta:
        model = GenericCollection
        fields = "__all__"


class AccreditationReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    author = FieldsRelatedField(["id", "first_name", "last_name"])
    linked_collection = FieldsRelatedField()
    checklist = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(["folder"], many=True)
    status = serializers.CharField(source="get_status_display")
    category = serializers.CharField(source="get_category_display")

    class Meta:
        model = Accreditation
        fields = "__all__"


class AccreditationWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Accreditation
        fields = "__all__"
