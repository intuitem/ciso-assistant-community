from core.serializer_fields import FieldsRelatedField
from core.serializers import (
    BaseModelSerializer,
)

from .models import (
    QuantitativeRiskAggregation,
    QuantitativeRiskHypothesis,
    QuantitativeRiskScenario,
    QuantitativeRiskStudy,
)


class QuantitativeRiskStudyWriteSerializer(BaseModelSerializer):
    class Meta:
        model = QuantitativeRiskStudy
        exclude = ["created_at", "updated_at"]


class QuantitativeRiskStudyReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    authors = FieldsRelatedField(many=True)
    reviewers = FieldsRelatedField(many=True)

    class Meta:
        model = QuantitativeRiskStudy
        fields = "__all__"


class QuantitativeRiskScenarioWriteSerializer(BaseModelSerializer):
    class Meta:
        model = QuantitativeRiskScenario
        exclude = ["created_at", "updated_at"]


class QuantitativeRiskScenarioReadSerializer(BaseModelSerializer):
    quantitative_risk_study = FieldsRelatedField()
    assets = FieldsRelatedField(many=True)
    threats = FieldsRelatedField(many=True)
    vulnerabilities = FieldsRelatedField(many=True)
    qualifications = FieldsRelatedField(many=True)


class QuantitativeRiskHypothesisWriteSerializer(BaseModelSerializer):
    class Meta:
        model = QuantitativeRiskHypothesis
        exclude = ["created_at", "updated_at"]


class QuantitativeRiskHypothesisReadSerializer(BaseModelSerializer):
    quantitative_risk_study = FieldsRelatedField()
    quantitative_risk_scenario = FieldsRelatedField()
    quantitative_risk_aggregations = FieldsRelatedField(many=True)
    existing_applied_controls = FieldsRelatedField(many=True)
    added_applied_controls = FieldsRelatedField(many=True)
    removed_applied_controls = FieldsRelatedField(many=True)

    class Meta:
        model = QuantitativeRiskHypothesis
        fields = "__all__"


class QuantitativeRiskAggregationWriteSerializer(BaseModelSerializer):
    class Meta:
        model = QuantitativeRiskAggregation
        exclude = ["created_at", "updated_at"]


class QuantitativeRiskAggregationReadSerializer(BaseModelSerializer):
    quantitative_risk_study = FieldsRelatedField()

    class Meta:
        model = QuantitativeRiskAggregation
        fields = "__all__"
