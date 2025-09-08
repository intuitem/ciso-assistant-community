from rest_framework import serializers
from core.serializer_fields import FieldsRelatedField
from core.serializers import (
    BaseModelSerializer,
)

from .models import (
    QuantitativeRiskHypothesis,
    QuantitativeRiskScenario,
    QuantitativeRiskStudy,
)
import json


class ImpactField(serializers.Field):
    """
    A custom field to serialize and deserialize the impact, which includes
    the distribution type and confidence interval bounds.
    """

    def to_representation(self, value):
        return value

    def to_internal_value(self, data):
        # Handle null/empty data
        if data is None or data == "":
            return None

        # Parse JSON string if needed
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Impact field must be valid JSON.")

        if not isinstance(data, dict):
            raise serializers.ValidationError("Impact must be a dictionary.")

        # Extract required fields
        distribution = data.get("distribution")
        lb = data.get("lb")
        ub = data.get("ub")

        # Check for missing fields - allow empty if all are missing (optional field)
        if distribution is None and lb is None and ub is None:
            return None

        # If any field is provided, all are required
        if not all([distribution, lb is not None, ub is not None]):
            raise serializers.ValidationError(
                "Impact requires 'distribution', 'lb', and 'ub' keys."
            )

        # Validate distribution type
        if distribution != "LOGNORMAL-CI90":
            raise serializers.ValidationError(
                "Only 'LOGNORMAL-CI90' distribution is supported."
            )

        # Validate numeric values
        if not all(isinstance(val, (int, float)) for val in [lb, ub]):
            raise serializers.ValidationError("'lb' and 'ub' must be numeric.")

        # Validate bounds logic
        if lb <= 0:
            raise serializers.ValidationError("Lower bound 'lb' must be positive.")

        if ub <= lb:
            raise serializers.ValidationError(
                "Upper bound 'ub' must be greater than 'lb'."
            )

        return data


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
    owner = FieldsRelatedField(many=True)
    threats = FieldsRelatedField(many=True)
    vulnerabilities = FieldsRelatedField(many=True)
    qualifications = FieldsRelatedField(many=True)
    folder = FieldsRelatedField()
    ale = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    display_ale = serializers.CharField(read_only=True)

    class Meta:
        model = QuantitativeRiskScenario
        fields = "__all__"


class QuantitativeRiskHypothesisWriteSerializer(BaseModelSerializer):
    probability = serializers.FloatField(
        source="parameters.probability", required=False, allow_null=True
    )
    impact = ImpactField(source="parameters.impact", required=False, allow_null=True)

    class Meta:
        model = QuantitativeRiskHypothesis
        fields = "__all__"


class QuantitativeRiskHypothesisReadSerializer(BaseModelSerializer):
    quantitative_risk_scenario = FieldsRelatedField()
    existing_applied_controls = FieldsRelatedField(many=True)
    added_applied_controls = FieldsRelatedField(many=True)
    removed_applied_controls = FieldsRelatedField(many=True)
    probability = serializers.FloatField(
        source="parameters.probability", read_only=True
    )
    impact = serializers.JSONField(source="parameters.impact", read_only=True)
    simulation_parameters_display = serializers.CharField(
        source="get_simulation_parameters_display", read_only=True
    )
    lec_data = serializers.SerializerMethodField()
    ale = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    treatment_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    treatment_cost_display = serializers.CharField(read_only=True)
    folder = FieldsRelatedField()

    def get_lec_data(self, obj):
        """Return LEC data for the table preview"""
        if not obj.simulation_data or not isinstance(obj.simulation_data, dict):
            return None

        loss_data = obj.simulation_data.get("loss", [])
        probability_data = obj.simulation_data.get("probability", [])

        if (
            not loss_data
            or not probability_data
            or len(loss_data) != len(probability_data)
        ):
            return None

        # Convert to [x, y] pairs for ECharts, same format as the LEC endpoint
        return [[loss, prob] for loss, prob in zip(loss_data, probability_data)]

    class Meta:
        model = QuantitativeRiskHypothesis
        fields = "__all__"
