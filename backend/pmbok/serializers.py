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
    findings_assessments = FieldsRelatedField(many=True)
    documents = FieldsRelatedField(many=True)
    security_exceptions = FieldsRelatedField(many=True)
    policies = FieldsRelatedField(many=True)
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
    authority = FieldsRelatedField()
    linked_collection = FieldsRelatedField()
    collection_data = serializers.SerializerMethodField()
    checklist = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(["folder"], many=True)
    status = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    checklist_progress = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.status.get_name_translated

    def get_category(self, obj):
        return obj.category.get_name_translated

    def get_collection_data(self, obj):
        """Get the linked collection with all related objects"""
        if obj.linked_collection:
            return GenericCollectionReadSerializer(obj.linked_collection).data
        return None

    def get_checklist_progress(self, obj):
        """Get the progress percentage of the checklist compliance assessment"""
        if obj.checklist:
            return obj.checklist.get_progress()
        return None

    class Meta:
        model = Accreditation
        fields = "__all__"


class AccreditationWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Accreditation
        fields = "__all__"
