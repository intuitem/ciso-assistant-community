from core.serializers import BaseModelSerializer, FieldsRelatedField, AssessmentReadSerializer
from .models import EbiosRMStudy
from rest_framework import serializers


class EbiosRMStudyWriteSerializer(BaseModelSerializer):
    class Meta:
        model = EbiosRMStudy
        exclude = ["created_at", "updated_at"]


class EbiosRMStudyReadSerializer(AssessmentReadSerializer):
    str = serializers.CharField(source="__str__")
    project = FieldsRelatedField(["id", "folder"])
    folder = FieldsRelatedField()
    risk_matrix = FieldsRelatedField()
    assets = FieldsRelatedField(many=True)
    compliance_assessments = FieldsRelatedField(many=True)
    risk_assessments = FieldsRelatedField(many=True)

    class Meta:
        model = EbiosRMStudy
        fields = "__all__"