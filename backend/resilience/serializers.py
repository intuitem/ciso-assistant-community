from core.serializers import BaseModelSerializer, AssessmentReadSerializer
from core.serializer_fields import FieldsRelatedField
from .models import (
    BusinessImpactAnalysis,
    EscalationThreshold,
    AssetAssessment,
)

from rest_framework import serializers


class BusinessImpactAnalysisReadSerializer(AssessmentReadSerializer):
    class Meta:
        model = BusinessImpactAnalysis
        exclude = []

    str = serializers.CharField(source="__str__")
    perimeter = FieldsRelatedField(["id", "folder"])
    folder = FieldsRelatedField()
    risk_matrix = FieldsRelatedField()


class BusinessImpactAnalysisWriteSerializer(BaseModelSerializer):
    class Meta:
        model = BusinessImpactAnalysis
        fields = "__all__"


class AssetAssessmentReadSerializer(BaseModelSerializer):
    bia = FieldsRelatedField()
    asset = FieldsRelatedField()
    folder = FieldsRelatedField()

    class Meta:
        model = AssetAssessment
        exclude = []


class AssetAssessmentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = AssetAssessment
        fields = "__all__"


class EscalationThresholdReadSerializer(BaseModelSerializer):
    class Meta:
        model = EscalationThreshold
        fields = "__all__"


class EscalationThresholdWriteSerializer(BaseModelSerializer):
    class Meta:
        model = EscalationThreshold
        fields = "__all__"
