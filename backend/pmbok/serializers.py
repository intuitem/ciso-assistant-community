from rest_framework import serializers

from core.serializers import BaseModelSerializer
from core.serializer_fields import FieldsRelatedField, PathField
from pmbok.models import GenericCollection, Accreditation


class GenericCollectionReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    compliance_assessments = FieldsRelatedField(["id", "status"], many=True)
    risk_assessments = FieldsRelatedField(["id", "status"], many=True)
    crq_studies = FieldsRelatedField(["id", "status"], many=True)
    ebios_studies = FieldsRelatedField(["id", "status"], many=True)
    entity_assessments = FieldsRelatedField(["id", "status"], many=True)
    findings_assessments = FieldsRelatedField(["id", "status"], many=True)
    documents = FieldsRelatedField(["id", "status"], many=True)
    security_exceptions = FieldsRelatedField(["id", "status"], many=True)
    policies = FieldsRelatedField(["id", "status"], many=True)
    dependencies = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)

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
    author = FieldsRelatedField()
    authority = FieldsRelatedField()
    linked_collection = FieldsRelatedField()
    collection_data = serializers.SerializerMethodField()
    checklist = FieldsRelatedField()
    decision_evidence = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)
    status = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    checklist_progress = serializers.SerializerMethodField()
    validation_flows = FieldsRelatedField(
        many=True,
        fields=[
            "id",
            "ref_id",
            "status",
            {"approver": ["id", "email", "first_name", "last_name"]},
        ],
        source="validationflow_set",
    )

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
            return obj.checklist.progress
        return None

    class Meta:
        model = Accreditation
        fields = "__all__"


class AccreditationWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Accreditation
        fields = "__all__"

    def validate(self, data):
        from dateutil.relativedelta import relativedelta

        commission_date = data.get(
            "commission_date",
            getattr(getattr(self, "instance", None), "commission_date", None),
        )
        duration_months = data.get(
            "duration_months",
            getattr(getattr(self, "instance", None), "duration_months", None),
        )

        # Auto-compute expiry_date when commission_date and duration_months are set
        # and expiry_date is empty/null (cleared or never provided)
        if commission_date and duration_months and not data.get("expiry_date"):
            data["expiry_date"] = commission_date + relativedelta(
                months=duration_months
            )

        return super().validate(data)
