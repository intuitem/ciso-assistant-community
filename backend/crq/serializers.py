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
    loss_threshold_display = serializers.CharField(read_only=True)

    class Meta:
        model = QuantitativeRiskStudy
        fields = "__all__"


class QuantitativeRiskScenarioWriteSerializer(BaseModelSerializer):
    class Meta:
        model = QuantitativeRiskScenario
        exclude = ["created_at", "updated_at"]

    def create(self, validated_data):
        # Create the quantitative risk scenario
        scenario = super().create(validated_data)

        # Automatically create an associated quantitative hypothesis with risk_stage='current'
        QuantitativeRiskHypothesis.objects.create(
            quantitative_risk_scenario=scenario,
            name="baseline",
            risk_stage="current",
            is_selected=True,
            ref_id=QuantitativeRiskHypothesis.get_default_ref_id(scenario),
            folder=scenario.folder,  # Use the same folder as the scenario
        )

        return scenario


class QuantitativeRiskScenarioReadSerializer(BaseModelSerializer):
    quantitative_risk_study = FieldsRelatedField()
    assets = FieldsRelatedField(many=True)
    owner = FieldsRelatedField(many=True)
    threats = FieldsRelatedField(many=True)
    vulnerabilities = FieldsRelatedField(many=True)
    qualifications = FieldsRelatedField(many=True)
    folder = FieldsRelatedField()
    current_ale = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    current_ale_display = serializers.CharField(read_only=True)
    residual_ale = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    residual_ale_display = serializers.CharField(read_only=True)

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

    def create(self, validated_data):
        # Check if this is a residual hypothesis and if parameters are not set
        risk_stage = validated_data.get("risk_stage")
        scenario = validated_data.get("quantitative_risk_scenario")
        parameters = validated_data.get("parameters", {})

        # Find the current hypothesis in the same scenario (for residual hypothesis logic)
        current_hypothesis = None
        if risk_stage == "residual" and scenario:
            current_hypothesis = QuantitativeRiskHypothesis.objects.filter(
                quantitative_risk_scenario=scenario, risk_stage="current"
            ).first()

        # If creating a residual hypothesis without parameters, copy from current hypothesis
        if (
            risk_stage == "residual"
            and scenario
            and current_hypothesis
            and (
                not parameters
                or (not parameters.get("probability") and not parameters.get("impact"))
            )
        ):
            # If current hypothesis exists, copy parameters and existing controls
            if current_hypothesis.parameters:
                current_params = current_hypothesis.parameters.copy()

                # Only copy if the user hasn't provided their own parameters
                if not parameters.get("probability") and current_params.get(
                    "probability"
                ):
                    if "parameters" not in validated_data:
                        validated_data["parameters"] = {}
                    validated_data["parameters"]["probability"] = current_params[
                        "probability"
                    ]

                if not parameters.get("impact") and current_params.get("impact"):
                    if "parameters" not in validated_data:
                        validated_data["parameters"] = {}
                    validated_data["parameters"]["impact"] = current_params[
                        "impact"
                    ].copy()

        # Create the hypothesis
        hypothesis = super().create(validated_data)

        # After creating the hypothesis, copy existing applied controls from current hypothesis
        # Only if the newly created residual hypothesis doesn't have existing controls set
        if (
            risk_stage == "residual"
            and scenario
            and current_hypothesis
            and current_hypothesis.existing_applied_controls.exists()
            and not hypothesis.existing_applied_controls.exists()
        ):
            # Copy all existing applied controls from current to residual as existing controls
            hypothesis.existing_applied_controls.set(
                current_hypothesis.existing_applied_controls.all()
            )

        return hypothesis

    def validate(self, attrs):
        """
        Validate that only one residual hypothesis per scenario can be selected at a time.
        """
        attrs = super().validate(attrs)

        # Only validate if is_selected is being set to True and risk_stage is residual
        is_selected = attrs.get("is_selected", False)
        risk_stage = attrs.get("risk_stage")
        scenario = attrs.get("quantitative_risk_scenario")

        if is_selected and risk_stage == "residual" and scenario:
            # Check if there are other selected residual hypotheses in the same scenario
            existing_selected_residual = QuantitativeRiskHypothesis.objects.filter(
                quantitative_risk_scenario=scenario,
                risk_stage="residual",
                is_selected=True,
            )

            # Exclude the current instance if we're updating
            if self.instance:
                existing_selected_residual = existing_selected_residual.exclude(
                    id=self.instance.id
                )

            if existing_selected_residual.exists():
                selected_hypothesis = existing_selected_residual.first()
                raise serializers.ValidationError(
                    {
                        "is_selected": f'Another residual hypothesis "{selected_hypothesis.name}" is already selected for this scenario. Only one residual hypothesis can be selected per scenario.'
                    }
                )

        if risk_stage == "current" and scenario:
            existing_current = QuantitativeRiskHypothesis.objects.filter(
                quantitative_risk_scenario=scenario, risk_stage="current"
            )
            # Exclude the current instance if we're updating
            if self.instance:
                existing_current = existing_current.exclude(id=self.instance.id)

            if existing_current.exists():
                current_hypothesis = existing_current.first()
                raise serializers.ValidationError(
                    {
                        "risk_stage": f'There is already a current hypothsis "{current_hypothesis.name}". Only one current is allowed.'
                    }
                )

        if risk_stage == "inherent" and scenario:
            existing_inherent = QuantitativeRiskHypothesis.objects.filter(
                quantitative_risk_scenario=scenario, risk_stage="inherent"
            )
            # Exclude the current instance if we're updating
            if self.instance:
                existing_inherent = existing_inherent.exclude(id=self.instance.id)

            if existing_inherent.exists():
                inherent_hypothesis = existing_inherent.first()
                raise serializers.ValidationError(
                    {
                        "risk_stage": f'There is already an inherent hypothsis "{inherent_hypothesis.name}". Only one inherent is allowed.'
                    }
                )
        return attrs


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
    ale_display = serializers.CharField(read_only=True)
    treatment_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    treatment_cost_display = serializers.CharField(read_only=True)
    roc = serializers.DecimalField(max_digits=12, decimal_places=4, read_only=True)
    roc_display = serializers.CharField(read_only=True)
    roc_interpretation = serializers.CharField(read_only=True)
    roc_calculation_explanation = serializers.CharField(read_only=True)
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

    loss_threshold = serializers.SerializerMethodField()
    loss_threshold_display = serializers.SerializerMethodField()

    def get_loss_threshold(self, obj):
        """Return loss threshold from parent study"""
        study = obj.quantitative_risk_scenario.quantitative_risk_study
        return study.loss_threshold if study else None

    def get_loss_threshold_display(self, obj):
        """Return formatted loss threshold from parent study"""
        study = obj.quantitative_risk_scenario.quantitative_risk_study
        return study.loss_threshold_display if study else None

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
