from rest_framework import serializers
from core.serializer_fields import FieldsRelatedField
from core.serializers import (
    BaseModelSerializer,
    ActionPlanSerializer,
)
from core.models import AppliedControl

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
    risk_tolerance_display = serializers.CharField(
        source="get_risk_tolerance_display", read_only=True
    )

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
    risk_tolerance_curve = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    ale = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    treatment_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    treatment_cost_display = serializers.CharField(read_only=True)
    roc = serializers.DecimalField(max_digits=12, decimal_places=4, read_only=True)
    roc_display = serializers.CharField(read_only=True)
    roc_interpretation = serializers.CharField(read_only=True)
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

    def get_risk_tolerance_curve(self, obj):
        """Return risk tolerance curve data from the parent study"""
        study = obj.quantitative_risk_scenario.quantitative_risk_study

        # Check if risk tolerance curve data exists
        if (
            not study.risk_tolerance
            or "curve_data" not in study.risk_tolerance
            or "error" in study.risk_tolerance.get("curve_data", {})
        ):
            return None

        curve_data = study.risk_tolerance["curve_data"]
        loss_data = curve_data.get("loss_values", [])
        probability_data = curve_data.get("probability_values", [])

        if (
            not loss_data
            or not probability_data
            or len(loss_data) != len(probability_data)
        ):
            return None

        # Convert to [x, y] pairs for ECharts, same format as the LEC endpoint
        return [[loss, prob] for loss, prob in zip(loss_data, probability_data)]

    def get_currency(self, obj):
        """Return currency symbol from global settings"""
        from global_settings.models import GlobalSettings

        general_settings = GlobalSettings.objects.filter(name="general").first()
        return general_settings.value.get("currency", "€") if general_settings else "€"

    class Meta:
        model = QuantitativeRiskHypothesis
        fields = "__all__"


class QuantitativeRiskStudyActionPlanSerializer(ActionPlanSerializer):
    """
    Serializer for CRQ action plan that shows controls with the scenarios they affect.
    """

    quantitative_risk_scenarios = serializers.SerializerMethodField()

    def get_quantitative_risk_scenarios(self, obj):
        """
        Get the quantitative risk scenarios affected by this control.
        """
        pk = self.context.get("pk")
        if pk is None:
            return []

        # Find hypotheses in this study that have this control as added control
        from .models import QuantitativeRiskStudy

        try:
            study = QuantitativeRiskStudy.objects.get(id=pk)
            scenarios = study.risk_scenarios.all()

            # Get hypotheses that have this control added
            hypotheses_with_control = QuantitativeRiskHypothesis.objects.filter(
                quantitative_risk_scenario__in=scenarios, added_applied_controls=obj
            )

            # Get unique scenarios from these hypotheses
            affected_scenarios = []
            seen_scenario_ids = set()

            for hypothesis in hypotheses_with_control:
                scenario = hypothesis.quantitative_risk_scenario
                if scenario.id not in seen_scenario_ids:
                    seen_scenario_ids.add(scenario.id)
                    affected_scenarios.append(
                        {
                            "str": f"{scenario.ref_id} - {scenario.name}",
                            "id": str(scenario.id),
                        }
                    )

            return affected_scenarios

        except Exception:
            return []
