from rest_framework import serializers

from core.serializers import BaseModelSerializer
from core.serializer_fields import IdRelatedField, PathField
from pmbok.models import GenericCollection, Accreditation


class GenericCollectionReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = IdRelatedField()
    compliance_assessments = IdRelatedField(many=True)
    risk_assessments = IdRelatedField(many=True)
    crq_studies = IdRelatedField(many=True)
    ebios_studies = IdRelatedField(many=True)
    entity_assessments = IdRelatedField(many=True)
    findings_assessments = IdRelatedField(many=True)
    documents = IdRelatedField(many=True)
    security_exceptions = IdRelatedField(many=True)
    policies = IdRelatedField(many=True)
    dependencies = IdRelatedField(many=True)
    filtering_labels = IdRelatedField(["folder"], many=True)

    class Meta:
        model = GenericCollection
        fields = "__all__"


class GenericCollectionWriteSerializer(BaseModelSerializer):
    class Meta:
        model = GenericCollection
        fields = "__all__"


class AccreditationReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = IdRelatedField()
    author = IdRelatedField(["id", "first_name", "last_name"])
    authority = IdRelatedField()
    linked_collection = IdRelatedField()
    collection_data = serializers.SerializerMethodField()
    checklist = IdRelatedField()
    filtering_labels = IdRelatedField(["folder"], many=True)
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
