import structlog

from rest_framework import status
from rest_framework.views import Response
from rest_framework.decorators import action
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db import transaction

from core.views import BaseModelViewSet as AbstractBaseModelViewSet, ActionPlanList
from core.models import AppliedControl
from global_settings.models import GlobalSettings

from .models import (
    QuantitativeRiskStudy,
    QuantitativeRiskScenario,
    QuantitativeRiskHypothesis,
)
from .serializers import QuantitativeRiskStudyActionPlanSerializer

logger = structlog.get_logger(__name__)

LONG_CACHE_TTL = 60  # Cache for 60 minutes


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "crq.serializers"


class QuantitativeRiskStudyViewSet(BaseModelViewSet):
    model = QuantitativeRiskStudy
    filterset_fields = [
        "folder",
        "authors",
        "reviewers",
        "status",
    ]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["-created_at"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(QuantitativeRiskStudy.Status.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get distribution model choices")
    def distribution_model(self, request):
        return Response(dict(QuantitativeRiskStudy.Distribution_model.choices))

    @action(detail=True, name="Combined ALE Metrics", url_path="combined-ale")
    def combined_ale(self, request, pk=None):
        """
        Returns combined ALE metrics for the quantitative risk study:
        - Current ALE Combined: Sum of current ALE from all scenarios
        - Residual ALE Combined: Sum of ALE from selected residual hypotheses per scenario
        """
        study: QuantitativeRiskStudy = self.get_object()  # type: ignore[unreachable]

        # Get currency from global settings
        general_settings = GlobalSettings.objects.filter(name="general").first()
        currency = (
            general_settings.value.get("currency", "€") if general_settings else "€"
        )

        # Initialize totals
        current_ale_combined = 0
        residual_ale_combined = 0
        scenarios_data = []

        # Process each scenario in the study
        for scenario in study.risk_scenarios.all():
            scenario_data = {
                "scenario_id": str(scenario.id),
                "scenario_name": scenario.name,
                "current_ale": None,
                "residual_ale": None,
                "residual_hypothesis_name": None,
            }

            # Get current ALE from the scenario (using the property)
            current_ale = scenario.current_ale
            if current_ale is not None:
                scenario_data["current_ale"] = current_ale
                current_ale_combined += current_ale

            # Get residual ALE from the scenario (using the property)
            residual_ale = scenario.residual_ale
            if residual_ale is not None:
                scenario_data["residual_ale"] = residual_ale
                residual_ale_combined += residual_ale

                # Get the selected residual hypothesis name for display
                selected_residual_hypothesis = scenario.hypotheses.filter(
                    risk_stage="residual", is_selected=True
                ).first()
                if selected_residual_hypothesis:
                    scenario_data["residual_hypothesis_name"] = (
                        selected_residual_hypothesis.name
                    )

            scenarios_data.append(scenario_data)

        # Format currency helper function
        def format_currency(value):
            if value >= 1000000000:
                return f"{currency}{value / 1000000000:.1f}B"
            elif value >= 1000000:
                return f"{currency}{value / 1000000:.1f}M"
            elif value >= 1000:
                return f"{currency}{value / 1000:.0f}K"
            else:
                return f"{currency}{value:,.0f}"

        return Response(
            {
                "study_id": str(study.id),
                "study_name": study.name,
                "currency": currency,
                "combined_metrics": {
                    "current_ale_combined": current_ale_combined,
                    "current_ale_combined_display": format_currency(
                        current_ale_combined
                    )
                    if current_ale_combined > 0
                    else "No current ALE data",
                    "residual_ale_combined": residual_ale_combined,
                    "residual_ale_combined_display": format_currency(
                        residual_ale_combined
                    )
                    if residual_ale_combined > 0
                    else "No residual ALE data",
                    "risk_reduction": current_ale_combined - residual_ale_combined
                    if current_ale_combined > 0 and residual_ale_combined > 0
                    else None,
                    "risk_reduction_display": format_currency(
                        current_ale_combined - residual_ale_combined
                    )
                    if current_ale_combined > 0 and residual_ale_combined > 0
                    else "Cannot calculate",
                },
                "scenarios": scenarios_data,
                "total_scenarios": len(scenarios_data),
                "scenarios_with_current_ale": sum(
                    1 for s in scenarios_data if s["current_ale"] is not None
                ),
                "scenarios_with_residual_ale": sum(
                    1 for s in scenarios_data if s["residual_ale"] is not None
                ),
            }
        )

    @action(
        detail=True, name="Combined Loss Exceedance Curves", url_path="combined-lec"
    )
    def combined_lec(self, request, pk=None):
        """
        Returns combined Loss Exceedance Curve data for the quantitative risk study:
        - Risk tolerance curve (if configured)
        - Sum of all current hypothesis LEC curves from study scenarios
        """
        study: QuantitativeRiskStudy = self.get_object()

        # Get currency from global settings
        general_settings = GlobalSettings.objects.filter(name="general").first()
        currency = (
            general_settings.value.get("currency", "€") if general_settings else "€"
        )

        curves = []

        # 1. Add study risk tolerance curve if available
        if study.risk_tolerance and "curve_data" in study.risk_tolerance:
            curve_data = study.risk_tolerance["curve_data"]
            if "error" not in curve_data:
                loss_values = curve_data.get("loss_values", [])
                probability_values = curve_data.get("probability_values", [])

                if loss_values and probability_values:
                    tolerance_data = [
                        [loss, prob]
                        for loss, prob in zip(loss_values, probability_values)
                        if loss > 0
                    ]
                    curves.append(
                        {
                            "name": "Risk Tolerance",
                            "type": "tolerance",
                            "data": tolerance_data,
                            "study_id": str(study.id),
                            "study_name": study.name,
                        }
                    )

        # 2. Use cached portfolio simulation for current risk
        portfolio_data = study.get_or_generate_portfolio_simulation()

        # Add current portfolio curve if available
        if portfolio_data.get("current") and not portfolio_data["current"].get("error"):
            current_data = portfolio_data["current"]
            loss_data = current_data.get("loss", [])
            probability_data = current_data.get("probability", [])

            if loss_data and probability_data:
                combined_data = [
                    [float(loss), float(prob)]
                    for loss, prob in zip(loss_data, probability_data)
                    if loss > 0
                ]
                curves.append(
                    {
                        "name": "Combined Current Risk",
                        "type": "combined_current",
                        "data": combined_data,
                        "study_id": str(study.id),
                        "study_name": study.name,
                        "component_scenarios": current_data.get("scenarios", []),
                        "total_scenarios": current_data.get("total_scenarios", 0),
                        "simulation_method": current_data.get("method", "cached"),
                    }
                )

        # 3. Use cached portfolio simulation for residual risk
        # Add residual portfolio curve if available from cache
        if portfolio_data.get("residual") and not portfolio_data["residual"].get(
            "error"
        ):
            residual_data = portfolio_data["residual"]
            residual_loss_data = residual_data.get("loss", [])
            residual_probability_data = residual_data.get("probability", [])

            if residual_loss_data and residual_probability_data:
                combined_residual_data = [
                    [float(loss), float(prob)]
                    for loss, prob in zip(residual_loss_data, residual_probability_data)
                    if loss > 0
                ]
                curves.append(
                    {
                        "name": "Combined Residual Risk",
                        "type": "combined_residual",
                        "data": combined_residual_data,
                        "study_id": str(study.id),
                        "study_name": study.name,
                        "component_scenarios": residual_data.get("scenarios", []),
                        "total_scenarios": residual_data.get("total_scenarios", 0),
                        "simulation_method": residual_data.get("method", "cached"),
                    }
                )

        # Determine which simulation method was primarily used
        simulation_methods_used = set()
        for curve in curves:
            if "simulation_method" in curve:
                simulation_methods_used.add(curve["simulation_method"])

        primary_method = (
            "direct_simulation"
            if "direct_simulation" in simulation_methods_used
            else "cached"
            if "cached" in simulation_methods_used
            else "none"
        )

        # Calculate scenario counts from portfolio data
        current_scenario_count = 0
        residual_scenario_count = 0
        current_threshold_probability = None
        residual_threshold_probability = None

        if portfolio_data.get("current") and not portfolio_data["current"].get("error"):
            current_scenario_count = portfolio_data["current"].get("total_scenarios", 0)
            # Get threshold probability from metrics if loss threshold is set
            current_metrics = portfolio_data["current"].get("metrics", {})
            current_threshold_probability = current_metrics.get("prob_above_threshold")

        if portfolio_data.get("residual") and not portfolio_data["residual"].get(
            "error"
        ):
            residual_scenario_count = portfolio_data["residual"].get(
                "total_scenarios", 0
            )
            # Get threshold probability from metrics if loss threshold is set
            residual_metrics = portfolio_data["residual"].get("metrics", {})
            residual_threshold_probability = residual_metrics.get(
                "prob_above_threshold"
            )

        # Return the combined curves data
        return Response(
            {
                "study_id": str(study.id),
                "study_name": study.name,
                "currency": currency,
                "curves": curves,
                "total_curves": len(curves),
                "scenarios_with_current_data": current_scenario_count,
                "scenarios_with_residual_data": residual_scenario_count,
                "total_scenarios": study.risk_scenarios.count(),
                "simulation_method": primary_method,
                "simulation_methods_used": list(simulation_methods_used),
                "loss_threshold": study.loss_threshold,
                "loss_threshold_display": study.loss_threshold_display,
                "current_threshold_probability": current_threshold_probability,
                "residual_threshold_probability": residual_threshold_probability,
                "current_threshold_probability_display": f"{current_threshold_probability * 100:.1f}%"
                if current_threshold_probability is not None
                else None,
                "residual_threshold_probability_display": f"{residual_threshold_probability * 100:.1f}%"
                if residual_threshold_probability is not None
                else None,
                "note": "Portfolio risk calculations using cached simulation results for optimal performance",
            }
        )

    @action(detail=True, name="Executive Summary", url_path="executive-summary")
    def executive_summary(self, request, pk=None):
        """
        Returns executive summary data for the quantitative risk study.
        Includes scenarios that are selected and not in draft status with:
        - Main information (ref_id, name, description)
        - Assets, threats, qualifications links
        - LEC chart data (current, selected residual, risk tolerance)
        - Current and residual ALE insights
        - Treatment cost of selected residual hypothesis
        """
        study: QuantitativeRiskStudy = self.get_object()

        # Get currency from global settings
        general_settings = GlobalSettings.objects.filter(name="general").first()
        currency = (
            general_settings.value.get("currency", "€") if general_settings else "€"
        )

        # Get all selected scenarios regardless of status, ordered by priority then ref_id
        selected_scenarios = study.risk_scenarios.filter(is_selected=True).order_by(
            "priority", "ref_id"
        )

        scenarios_data = []
        all_study_assets = set()  # Collect unique assets across all scenarios
        all_added_controls = (
            set()
        )  # Track unique controls to avoid duplication in total cost
        all_removed_controls = (
            set()
        )  # Track unique controls removed to calculate savings
        total_treatment_cost = 0  # Track total treatment cost across all scenarios

        for scenario in selected_scenarios:
            scenario_info = {
                "id": str(scenario.id),
                "ref_id": scenario.ref_id,
                "name": scenario.name,
                "description": scenario.description,
                "observation": scenario.observation,
                "status": scenario.status,
                "priority": scenario.priority,
                # Assets, threats, qualifications
                "assets": [
                    {"id": str(asset.id), "name": asset.name}
                    for asset in scenario.assets.all()
                ],
                "threats": [
                    {"id": str(threat.id), "name": threat.name}
                    for threat in scenario.threats.all()
                ],
                "qualifications": [
                    {"id": str(qual.id), "name": qual.name}
                    for qual in scenario.qualifications.all()
                ],
                # ALE insights
                "current_ale": scenario.current_ale,
                "current_ale_display": scenario.current_ale_display,
                "residual_ale": scenario.residual_ale,
                "residual_ale_display": scenario.residual_ale_display,
            }

            # Collect unique assets for study-wide summary
            for asset in scenario.assets.all():
                all_study_assets.add((str(asset.id), asset.name))

            # Calculate risk reduction (current - residual)
            current_ale = scenario.current_ale
            residual_ale = scenario.residual_ale
            if current_ale is not None and residual_ale is not None:
                risk_reduction = current_ale - residual_ale
                scenario_info["risk_reduction"] = risk_reduction

                # Format risk reduction display
                def format_currency(value):
                    if value >= 1000000000:
                        return f"{currency}{value / 1000000000:.1f}B"
                    elif value >= 1000000:
                        return f"{currency}{value / 1000000:.1f}M"
                    elif value >= 1000:
                        return f"{currency}{value / 1000:.0f}K"
                    else:
                        return f"{currency}{value:,.0f}"

                scenario_info["risk_reduction_display"] = (
                    format_currency(risk_reduction)
                    if risk_reduction > 0
                    else format_currency(risk_reduction)
                )
            else:
                scenario_info["risk_reduction"] = None
                scenario_info["risk_reduction_display"] = "Cannot calculate"

            # Get controls information from hypotheses
            current_hypothesis = scenario.hypotheses.filter(
                risk_stage="current"
            ).first()
            selected_residual_hypothesis = scenario.hypotheses.filter(
                risk_stage="residual", is_selected=True
            ).first()

            # Existing controls from current hypothesis
            if current_hypothesis:
                scenario_info["existing_controls"] = [
                    {
                        "id": str(control.id),
                        "name": control.name,
                        "category": getattr(control.category, "name", None)
                        if control.category
                        else None,
                        "status": control.status,
                    }
                    for control in current_hypothesis.existing_applied_controls.all()
                ]
            else:
                scenario_info["existing_controls"] = []

            # Additional controls from selected residual hypothesis
            if selected_residual_hypothesis:
                scenario_info["additional_controls"] = [
                    {
                        "id": str(control.id),
                        "name": control.name,
                        "category": getattr(control.category, "name", None)
                        if control.category
                        else None,
                        "status": control.status,
                        "annual_cost": control.annual_cost,
                    }
                    for control in selected_residual_hypothesis.added_applied_controls.all()
                ]

                # Track unique controls for study-wide cost calculation
                for (
                    control
                ) in selected_residual_hypothesis.added_applied_controls.all():
                    all_added_controls.add(control.id)

                for (
                    control
                ) in selected_residual_hypothesis.removed_applied_controls.all():
                    all_removed_controls.add(control.id)
            else:
                scenario_info["additional_controls"] = []

            # LEC chart data
            lec_curves = []

            # Current hypothesis curve (reuse the variable from above)
            if current_hypothesis and current_hypothesis.simulation_data:
                simulation_data = current_hypothesis.simulation_data
                loss_data = simulation_data.get("loss", [])
                probability_data = simulation_data.get("probability", [])

                if loss_data and probability_data:
                    chart_data = [
                        [loss, prob]
                        for loss, prob in zip(loss_data, probability_data)
                        if loss > 0
                    ]
                    lec_curves.append(
                        {
                            "name": "Current Risk",
                            "type": "current",
                            "data": chart_data,
                            "hypothesis_id": str(current_hypothesis.id),
                            "hypothesis_name": current_hypothesis.name,
                            "metrics": simulation_data.get("metrics", {}),
                        }
                    )

            # Selected residual hypothesis curve (reuse the variable from above)
            if (
                selected_residual_hypothesis
                and selected_residual_hypothesis.simulation_data
            ):
                simulation_data = selected_residual_hypothesis.simulation_data
                loss_data = simulation_data.get("loss", [])
                probability_data = simulation_data.get("probability", [])

                if loss_data and probability_data:
                    chart_data = [
                        [loss, prob]
                        for loss, prob in zip(loss_data, probability_data)
                        if loss > 0
                    ]
                    lec_curves.append(
                        {
                            "name": "Selected Residual Risk",
                            "type": "residual",
                            "data": chart_data,
                            "hypothesis_id": str(selected_residual_hypothesis.id),
                            "hypothesis_name": selected_residual_hypothesis.name,
                            "metrics": simulation_data.get("metrics", {}),
                        }
                    )

                # Treatment cost
                scenario_info["treatment_cost"] = (
                    selected_residual_hypothesis.treatment_cost
                )
                scenario_info["treatment_cost_display"] = (
                    selected_residual_hypothesis.treatment_cost_display
                )

            # Risk tolerance curve (same for all scenarios)
            if study.risk_tolerance and "curve_data" in study.risk_tolerance:
                curve_data = study.risk_tolerance["curve_data"]
                if "error" not in curve_data:
                    loss_values = curve_data.get("loss_values", [])
                    probability_values = curve_data.get("probability_values", [])

                    if loss_values and probability_values:
                        tolerance_data = [
                            [loss, prob]
                            for loss, prob in zip(loss_values, probability_values)
                            if loss > 0
                        ]
                        lec_curves.append(
                            {
                                "name": "Risk Tolerance",
                                "type": "tolerance",
                                "data": tolerance_data,
                                "study_id": str(study.id),
                                "study_name": study.name,
                            }
                        )

            scenario_info["lec_curves"] = lec_curves
            scenarios_data.append(scenario_info)

        # Calculate total treatment cost based on unique controls (avoiding duplication)
        from core.models import AppliedControl

        study_total_treatment_cost = 0

        # Add costs of unique added controls
        if all_added_controls:
            added_controls = AppliedControl.objects.filter(id__in=all_added_controls)
            study_total_treatment_cost += sum(
                control.annual_cost
                for control in added_controls
                if control.annual_cost is not None
            )

        # Subtract costs of unique removed controls (savings)
        if all_removed_controls:
            removed_controls = AppliedControl.objects.filter(
                id__in=all_removed_controls
            )
            study_total_treatment_cost -= sum(
                control.annual_cost
                for control in removed_controls
                if control.annual_cost is not None
            )

        # Format study total treatment cost
        def format_currency(value):
            if value >= 1000000000:
                return f"{currency}{value / 1000000000:.1f}B"
            elif value >= 1000000:
                return f"{currency}{value / 1000000:.1f}M"
            elif value >= 1000:
                return f"{currency}{value / 1000:.0f}K"
            else:
                return f"{currency}{value:,.0f}"

        study_total_treatment_cost_display = (
            format_currency(study_total_treatment_cost)
            if study_total_treatment_cost != 0
            else "--"
        )

        return Response(
            {
                "study_id": str(study.id),
                "study_name": study.name,
                "study_description": study.description,
                "study_authors": [author.email for author in study.authors.all()],
                "study_folder": {"id": str(study.folder.id), "name": study.folder.name}
                if study.folder
                else None,
                "study_assets": [
                    {"id": asset_id, "name": asset_name}
                    for asset_id, asset_name in sorted(
                        all_study_assets, key=lambda x: x[1]
                    )
                ],
                "currency": currency,
                "risk_tolerance_display": study.get_risk_tolerance_display(),
                "loss_threshold": study.loss_threshold,
                "loss_threshold_display": study.loss_threshold_display,
                "scenarios": scenarios_data,
                "total_scenarios": len(scenarios_data),
                "total_selected_scenarios": study.risk_scenarios.filter(
                    is_selected=True
                ).count(),
                "total_draft_scenarios": study.risk_scenarios.filter(
                    status="draft"
                ).count(),
                "study_total_treatment_cost": study_total_treatment_cost,
                "study_total_treatment_cost_display": study_total_treatment_cost_display,
                "unique_added_controls_count": len(all_added_controls),
                "unique_removed_controls_count": len(all_removed_controls),
            }
        )

    @action(detail=True, name="Key Metrics Data", url_path="key-metrics")
    def key_metrics_data(self, request, pk=None):
        """
        Returns key metrics data for quantitative risk scenarios scoped per study.
        Provides the following info per scenario based on risk metrics:
        - name
        - ale (Annual Loss Expectancy)
        - var_95 (Value at Risk 95%)
        - var_99 (Value at Risk 99%)
        - var_999 (Value at Risk 99.9%)
        - proba_of_exceeding_threshold (Probability of exceeding the loss threshold)

        Data is provided for both current and residual risk levels based on risk_stage.
        Current level uses hypothesis with risk_stage='current'
        Residual level uses hypothesis with risk_stage='residual' and is_selected=True
        """
        study: QuantitativeRiskStudy = self.get_object()

        # Get currency from global settings
        general_settings = GlobalSettings.objects.filter(name="general").first()
        currency = (
            general_settings.value.get("currency", "€") if general_settings else "€"
        )

        scenarios_data = []

        # Process each scenario in the study
        for scenario in study.risk_scenarios.all():
            scenario_info = {
                "id": str(scenario.id),
                "name": scenario.name,
                "current_level": None,
                "residual_level": None,
            }

            # Get current level data (risk_stage = 'current')
            current_hypothesis = scenario.hypotheses.filter(
                risk_stage="current"
            ).first()
            if current_hypothesis and current_hypothesis.simulation_data:
                metrics = current_hypothesis.simulation_data.get("metrics", {})
                loss_threshold = study.loss_threshold

                current_data = {
                    "ale": metrics.get("mean_annual_loss"),
                    "var_95": metrics.get("var_95"),
                    "var_99": metrics.get("var_99"),
                    "var_999": metrics.get("var_999"),
                    "proba_of_exceeding_threshold": metrics.get("prob_above_threshold")
                    if loss_threshold
                    else None,
                    "hypothesis_id": str(current_hypothesis.id),
                    "hypothesis_name": current_hypothesis.name,
                }
                scenario_info["current_level"] = current_data

            # Get residual level data (risk_stage = 'residual' and is_selected = True)
            residual_hypothesis = scenario.hypotheses.filter(
                risk_stage="residual", is_selected=True
            ).first()
            if residual_hypothesis and residual_hypothesis.simulation_data:
                metrics = residual_hypothesis.simulation_data.get("metrics", {})
                loss_threshold = study.loss_threshold

                residual_data = {
                    "ale": metrics.get("mean_annual_loss"),
                    "var_95": metrics.get("var_95"),
                    "var_99": metrics.get("var_99"),
                    "var_999": metrics.get("var_999"),
                    "proba_of_exceeding_threshold": metrics.get("prob_above_threshold")
                    if loss_threshold
                    else None,
                    "hypothesis_id": str(residual_hypothesis.id),
                    "hypothesis_name": residual_hypothesis.name,
                }
                scenario_info["residual_level"] = residual_data

            scenarios_data.append(scenario_info)

        return Response(
            {
                "study_id": str(study.id),
                "study_name": study.name,
                "currency": currency,
                "loss_threshold": study.loss_threshold,
                "loss_threshold_display": study.loss_threshold_display,
                "scenarios": scenarios_data,
                "total_scenarios": len(scenarios_data),
                "scenarios_with_current_data": sum(
                    1 for s in scenarios_data if s["current_level"] is not None
                ),
                "scenarios_with_residual_data": sum(
                    1 for s in scenarios_data if s["residual_level"] is not None
                ),
                "note": "ALE = Annual Loss Expectancy, VaR = Value at Risk at specified percentiles, proba_of_exceeding_threshold calculated only if study has loss_threshold configured",
            }
        )


class QuantitativeRiskScenarioViewSet(BaseModelViewSet):
    model = QuantitativeRiskScenario
    filterset_fields = [
        "quantitative_risk_study",
        "assets",
        "threats",
        "vulnerabilities",
        "qualifications",
        "status",
        "priority",
        "is_selected",
    ]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["-created_at"]

    def _perform_write(self, serializer):
        if not serializer.validated_data.get(
            "ref_id"
        ) and serializer.validated_data.get("quantitative_risk_study"):
            quantitative_risk_study = serializer.validated_data[
                "quantitative_risk_study"
            ]
            ref_id = QuantitativeRiskScenario.get_default_ref_id(
                quantitative_risk_study
            )
            serializer.validated_data["ref_id"] = ref_id
        serializer.save()

    def perform_create(self, serializer):
        return self._perform_write(serializer)

    def perform_update(self, serializer):
        return self._perform_write(serializer)

    @action(detail=False, methods=["get"])
    def default_ref_id(self, request):
        quantitative_risk_study_id = request.query_params.get("quantitative_risk_study")
        if not quantitative_risk_study_id:
            return Response(
                {"error": "Missing 'quantitative_risk_study' parameter."}, status=400
            )
        try:
            quantitative_risk_study = QuantitativeRiskStudy.objects.get(
                pk=quantitative_risk_study_id
            )

            # Use the class method to compute the default ref_id
            default_ref_id = QuantitativeRiskScenario.get_default_ref_id(
                quantitative_risk_study
            )
            return Response({"results": default_ref_id})
        except Exception as e:
            logger.error("Error in default_ref_id: %s", str(e))
            return Response(
                {"error": "Error in default_ref_id has occurred."}, status=400
            )

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(QuantitativeRiskScenario.STATUS_OPTIONS))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get priority choices")
    def priority(self, request):
        return Response(dict(QuantitativeRiskScenario.PRIORITY))

    @action(detail=True, name="Combined Loss Exceedance Curves", url_path="lec")
    def lec(self, request, pk=None):
        """
        Returns combined Loss Exceedance Curve data for the scenario:
        - Inherent hypothesis curve (if available and has simulation data)
        - Current hypothesis curve (if available and has simulation data)
        - Study risk tolerance curve (if configured)
        - All residual hypothesis curves (if they have simulation data)
        """
        scenario: QuantitativeRiskScenario = self.get_object()
        study = scenario.quantitative_risk_study

        curves = []

        # 1. Add inherent hypothesis curve if available
        inherent_hypothesis = scenario.hypotheses.filter(risk_stage="inherent").first()
        if inherent_hypothesis and inherent_hypothesis.simulation_data:
            simulation_data = inherent_hypothesis.simulation_data
            loss_data = simulation_data.get("loss", [])
            probability_data = simulation_data.get("probability", [])

            if loss_data and probability_data:
                chart_data = [
                    [loss, prob]
                    for loss, prob in zip(loss_data, probability_data)
                    if loss > 0
                ]
                curves.append(
                    {
                        "name": "Inherent Risk",
                        "type": "inherent",
                        "data": chart_data,
                        "hypothesis_id": str(inherent_hypothesis.id),
                        "hypothesis_name": inherent_hypothesis.name,
                        "metrics": simulation_data.get("metrics", {}),
                    }
                )

        # 2. Add current hypothesis curve if available
        current_hypothesis = scenario.hypotheses.filter(risk_stage="current").first()
        if current_hypothesis and current_hypothesis.simulation_data:
            simulation_data = current_hypothesis.simulation_data
            loss_data = simulation_data.get("loss", [])
            probability_data = simulation_data.get("probability", [])

            if loss_data and probability_data:
                chart_data = [
                    [loss, prob]
                    for loss, prob in zip(loss_data, probability_data)
                    if loss > 0
                ]
                curves.append(
                    {
                        "name": "Current Risk",
                        "type": "current",
                        "data": chart_data,
                        "hypothesis_id": str(current_hypothesis.id),
                        "hypothesis_name": current_hypothesis.name,
                        "metrics": simulation_data.get("metrics", {}),
                    }
                )

        # 3. Add study risk tolerance curve if available
        if study.risk_tolerance and "curve_data" in study.risk_tolerance:
            curve_data = study.risk_tolerance["curve_data"]
            if "error" not in curve_data:
                loss_values = curve_data.get("loss_values", [])
                probability_values = curve_data.get("probability_values", [])

                if loss_values and probability_values:
                    tolerance_data = [
                        [loss, prob]
                        for loss, prob in zip(loss_values, probability_values)
                        if loss > 0
                    ]
                    curves.append(
                        {
                            "name": "Risk Tolerance",
                            "type": "tolerance",
                            "data": tolerance_data,
                            "study_id": str(study.id),
                            "study_name": study.name,
                        }
                    )

        # 4. Add all residual hypothesis curves
        residual_hypotheses = scenario.hypotheses.filter(risk_stage="residual").exclude(
            simulation_data__isnull=True
        )

        for residual_hypothesis in residual_hypotheses:
            if residual_hypothesis.simulation_data:
                simulation_data = residual_hypothesis.simulation_data
                loss_data = simulation_data.get("loss", [])
                probability_data = simulation_data.get("probability", [])

                if loss_data and probability_data:
                    chart_data = [
                        [loss, prob]
                        for loss, prob in zip(loss_data, probability_data)
                        if loss > 0
                    ]
                    curves.append(
                        {
                            "name": f"Residual - {residual_hypothesis.name}",
                            "type": "residual",
                            "data": chart_data,
                            "hypothesis_id": str(residual_hypothesis.id),
                            "hypothesis_name": residual_hypothesis.name,
                            "is_selected": residual_hypothesis.is_selected,
                            "metrics": simulation_data.get("metrics", {}),
                        }
                    )

        # Get currency from global settings
        general_settings = GlobalSettings.objects.filter(name="general").first()
        currency = (
            general_settings.value.get("currency", "€") if general_settings else "€"
        )

        # Return the combined curves data
        return Response(
            {
                "curves": curves,
                "scenario_id": str(scenario.id),
                "scenario_name": scenario.name,
                "study_name": study.name,
                "total_curves": len(curves),
                "currency": currency,
            }
        )


class QuantitativeRiskHypothesisViewSet(BaseModelViewSet):
    model = QuantitativeRiskHypothesis
    filterset_fields = ["quantitative_risk_scenario", "risk_stage", "is_selected"]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["-created_at"]

    def _perform_write(self, serializer):
        if not serializer.validated_data.get(
            "ref_id"
        ) and serializer.validated_data.get("quantitative_risk_scenario"):
            quantitative_risk_scenario = serializer.validated_data[
                "quantitative_risk_scenario"
            ]
            ref_id = QuantitativeRiskHypothesis.get_default_ref_id(
                quantitative_risk_scenario
            )
            serializer.validated_data["ref_id"] = ref_id
        serializer.save()

    def perform_create(self, serializer):
        return self._perform_write(serializer)

    def perform_update(self, serializer):
        return self._perform_write(serializer)

    @action(detail=False, methods=["get"])
    def default_ref_id(self, request):
        quantitative_risk_scenario_id = request.query_params.get(
            "quantitative_risk_scenario"
        )
        if not quantitative_risk_scenario_id:
            return Response(
                {"error": "Missing 'quantitative_risk_scenario' parameter."}, status=400
            )
        try:
            quantitative_risk_scenario = QuantitativeRiskScenario.objects.get(
                pk=quantitative_risk_scenario_id
            )

            # Use the class method to compute the default ref_id
            default_ref_id = QuantitativeRiskHypothesis.get_default_ref_id(
                quantitative_risk_scenario
            )
            return Response({"results": default_ref_id})
        except Exception as e:
            logger.error("Error in default_ref_id: %s", str(e))
            return Response(
                {"error": "Error in default_ref_id has occurred."}, status=400
            )

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get risk stage choices")
    def risk_stage(self, request):
        return Response(dict(QuantitativeRiskHypothesis.RISK_STAGE_OPTIONS))

    @action(detail=True, name="Loss Exceedance Curve", url_path="lec")
    def lec(self, request, pk=None):
        """
        Returns the Loss Exceedance Curve data from stored simulation results.
        Returns empty data if simulation is not fresh (parameters have changed).
        """
        hypothesis: QuantitativeRiskHypothesis = self.get_object()

        # Check if simulation data is fresh - if not, return empty data
        if not hypothesis.is_simulation_fresh or not hypothesis.simulation_data:
            return Response(
                {
                    "data": [],
                    "metrics": {},
                    "parameters_used": {},
                    "simulation_timestamp": "",
                    "message": "Parameters have changed. Please run a new simulation to see updated results."
                    if not hypothesis.is_simulation_fresh
                    else "No simulation data available. Please run a simulation first.",
                    "is_simulation_fresh": hypothesis.is_simulation_fresh,
                }
            )

        # Extract LEC data from stored simulation
        simulation_data = hypothesis.simulation_data
        loss_data = simulation_data.get("loss", [])
        probability_data = simulation_data.get("probability", [])

        # Transform data into chart-ready format: array of [loss, probability] tuples
        # Filter out zero loss values to start with meaningful data
        chart_data = []
        if loss_data and probability_data:
            chart_data = [
                [loss, prob]
                for loss, prob in zip(loss_data, probability_data)
                if loss > 0
            ]

        return Response(
            {
                "data": chart_data,
                "metrics": simulation_data.get("metrics", {}),
                "parameters_used": simulation_data.get("parameters_used", {}),
                "simulation_timestamp": simulation_data.get("simulation_timestamp", ""),
                "is_simulation_fresh": hypothesis.is_simulation_fresh,
            }
        )

    @action(detail=True, methods=["get"], url_path="run-simulation")
    def run_simulation(self, request, pk=None):
        """
        Triggers a Monte Carlo simulation for a specific risk hypothesis.
        Requires probability and impact parameters to be set on the hypothesis.
        """
        hypothesis: QuantitativeRiskHypothesis = self.get_object()

        try:
            # Run the simulation and ensure the data is saved
            with transaction.atomic():
                simulation_results = hypothesis.run_simulation(dry_run=False)
                # Force save to database within the transaction
                hypothesis.refresh_from_db()

            return Response(
                {
                    "success": True,
                    "message": "Simulation completed successfully",
                    "results_preview": {
                        "total_data_points": len(simulation_results["loss"]),
                        "metrics": simulation_results.get("metrics", {}),
                        "parameters_used": simulation_results.get(
                            "parameters_used", {}
                        ),
                    },
                }
            )
        except ValueError as e:
            # Handle parameter validation errors specifically
            logger.warning(
                "Parameter validation error for hypothesis %s: %s", pk, str(e)
            )
            return Response(
                {
                    "success": False,
                    "error": "Invalid parameters",
                    "details": str(e),
                    "hint": "Please ensure the hypothesis has valid probability and impact parameters (probability, impact.distribution='LOGNORMAL-CI90', impact.lb, impact.ub)",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            # Handle other errors
            logger.error("Error running simulation for hypothesis %s: %s", pk, str(e))
            return Response(
                {
                    "success": False,
                    "error": "Failed to run simulation",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class QuantitativeRiskStudyActionPlanList(ActionPlanList):
    """
    Action plan for quantitative risk studies.
    Returns controls from hypotheses in the study.
    """

    def get_serializer_class(self):
        return QuantitativeRiskStudyActionPlanSerializer

    def get_queryset(self):
        quantitative_risk_study: QuantitativeRiskStudy = (
            QuantitativeRiskStudy.objects.get(id=self.kwargs["pk"])
        )

        # Get all scenarios for this study
        scenarios = quantitative_risk_study.risk_scenarios.all()

        # Get all hypotheses from these scenarios that are selected
        hypotheses = QuantitativeRiskHypothesis.objects.filter(
            quantitative_risk_scenario__in=scenarios, is_selected=True
        )

        # Get all added controls from these selected hypotheses
        return AppliedControl.objects.filter(
            quantitative_risk_hypotheses_added__in=hypotheses
        ).distinct()
