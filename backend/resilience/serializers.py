from core.serializers import BaseModelSerializer
from core.serializer_fields import FieldsRelatedField
from .models import (
    BusinessImpactAnalysis,
    EscalationThreshold,
    AssetAssessment,
)


class BusinessImpactAnalysisReadSerializer(BaseModelSerializer):
    class Meta:
        model = BusinessImpactAnalysis
        fields = "__all__"


class BusinessImpactAnalysisWriteSerializer(BaseModelSerializer):
    class Meta:
        model = BusinessImpactAnalysis
        fields = "__all__"


class AssetAssessmentReadSerializer(BaseModelSerializer):
    class Meta:
        model = AssetAssessment
        fields = "__all__"


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
