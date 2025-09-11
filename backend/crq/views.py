from rest_framework import status, generics
from rest_framework.views import Response
from core.views import BaseModelViewSet as AbstractBaseModelViewSet, ActionPlanList
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import time
from .models import (
    QuantitativeRiskStudy,
    QuantitativeRiskScenario,
    QuantitativeRiskHypothesis,
)
from core.models import AppliedControl

from rest_framework.decorators import action

import structlog
import numpy as np
from .utils import sum_lec_curves

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
        study = self.get_object()

        # Get currency from global settings
        from global_settings.models import GlobalSettings

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
        study = self.get_object()

        # Get currency from global settings
        from global_settings.models import GlobalSettings

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

        # 2. Collect all current hypothesis LEC curves for summing
        current_curves_data = []
        scenarios_with_current = []

        for scenario in study.risk_scenarios.all():
            current_hypothesis = scenario.hypotheses.filter(
                risk_stage="current"
            ).first()
            if current_hypothesis and current_hypothesis.simulation_data:
                simulation_data = current_hypothesis.simulation_data
                loss_data = simulation_data.get("loss", [])
                probability_data = simulation_data.get("probability", [])

                if loss_data and probability_data:
                    # Convert to numpy arrays for curve summing
                    loss_array = np.array(loss_data)
                    prob_array = np.array(probability_data)

                    # Filter out zero losses
                    valid_indices = loss_array > 0
                    if np.any(valid_indices):
                        current_curves_data.append(
                            (loss_array[valid_indices], prob_array[valid_indices])
                        )
                        scenarios_with_current.append(
                            {
                                "scenario_id": str(scenario.id),
                                "scenario_name": scenario.name,
                                "hypothesis_id": str(current_hypothesis.id),
                                "hypothesis_name": current_hypothesis.name,
                            }
                        )

        # 3. Sum all current hypothesis curves if we have any
        if current_curves_data:
            try:
                combined_losses, combined_probs = sum_lec_curves(current_curves_data)

                if len(combined_losses) > 0 and len(combined_probs) > 0:
                    # Convert to chart-ready format
                    combined_data = [
                        [float(loss), float(prob)]
                        for loss, prob in zip(combined_losses, combined_probs)
                        if loss > 0
                    ]
                    curves.append(
                        {
                            "name": "Combined Current Risk",
                            "type": "combined_current",
                            "data": combined_data,
                            "study_id": str(study.id),
                            "study_name": study.name,
                            "component_scenarios": scenarios_with_current,
                            "total_scenarios": len(scenarios_with_current),
                        }
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to sum LEC curves for study {study.id}: {str(e)}"
                )

        # 4. Collect all selected residual hypothesis LEC curves for summing
        residual_curves_data = []
        scenarios_with_residual = []

        for scenario in study.risk_scenarios.all():
            selected_residual_hypothesis = scenario.hypotheses.filter(
                risk_stage="residual", is_selected=True
            ).first()
            if (
                selected_residual_hypothesis
                and selected_residual_hypothesis.simulation_data
            ):
                simulation_data = selected_residual_hypothesis.simulation_data
                loss_data = simulation_data.get("loss", [])
                probability_data = simulation_data.get("probability", [])

                if loss_data and probability_data:
                    # Convert to numpy arrays for curve summing
                    loss_array = np.array(loss_data)
                    prob_array = np.array(probability_data)

                    # Filter out zero losses
                    valid_indices = loss_array > 0
                    if np.any(valid_indices):
                        residual_curves_data.append(
                            (loss_array[valid_indices], prob_array[valid_indices])
                        )
                        scenarios_with_residual.append(
                            {
                                "scenario_id": str(scenario.id),
                                "scenario_name": scenario.name,
                                "hypothesis_id": str(selected_residual_hypothesis.id),
                                "hypothesis_name": selected_residual_hypothesis.name,
                            }
                        )

        # 5. Sum all selected residual hypothesis curves if we have any
        if residual_curves_data:
            try:
                combined_residual_losses, combined_residual_probs = sum_lec_curves(
                    residual_curves_data
                )

                if (
                    len(combined_residual_losses) > 0
                    and len(combined_residual_probs) > 0
                ):
                    # Convert to chart-ready format
                    combined_residual_data = [
                        [float(loss), float(prob)]
                        for loss, prob in zip(
                            combined_residual_losses, combined_residual_probs
                        )
                        if loss > 0
                    ]
                    curves.append(
                        {
                            "name": "Combined Residual Risk",
                            "type": "combined_residual",
                            "data": combined_residual_data,
                            "study_id": str(study.id),
                            "study_name": study.name,
                            "component_scenarios": scenarios_with_residual,
                            "total_scenarios": len(scenarios_with_residual),
                        }
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to sum residual LEC curves for study {study.id}: {str(e)}"
                )

        # Return the combined curves data
        return Response(
            {
                "study_id": str(study.id),
                "study_name": study.name,
                "currency": currency,
                "curves": curves,
                "total_curves": len(curves),
                "scenarios_with_current_data": len(scenarios_with_current),
                "scenarios_with_residual_data": len(scenarios_with_residual),
                "total_scenarios": study.risk_scenarios.count(),
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

    @action(detail=True, name="Combined Loss Exceedance Curves", url_path="lec")
    def lec(self, request, pk=None):
        """
        Returns combined Loss Exceedance Curve data for the scenario:
        - Current hypothesis curve (if available and has simulation data)
        - Study risk tolerance curve (if configured)
        - All residual hypothesis curves (if they have simulation data)
        """
        scenario = self.get_object()
        study = scenario.quantitative_risk_study

        curves = []

        # 1. Add current hypothesis curve if available
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

        # 2. Add study risk tolerance curve if available
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

        # 3. Add all residual hypothesis curves
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
        from global_settings.models import GlobalSettings

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
        """
        hypothesis = self.get_object()

        # Check if we have simulation data
        if not hypothesis.simulation_data:
            return Response(
                {
                    "data": [],
                    "message": "No simulation data available. Please run a simulation first.",
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
            }
        )

    @action(detail=True, methods=["get"], url_path="run-simulation")
    def run_simulation(self, request, pk=None):
        """
        Triggers a Monte Carlo simulation for a specific risk hypothesis.
        Requires probability and impact parameters to be set on the hypothesis.
        """
        hypothesis = self.get_object()

        try:
            # Run the simulation (this will save the results to the database)
            simulation_results = hypothesis.run_simulation(dry_run=False)

            # Add a small delay to simulate processing time
            time.sleep(2)

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

    # Override to exclude cost field which causes JSONField filtering issues
    # filterset_fields = {
    #     field: lookups
    #     for field, lookups in ActionPlanList.filterset_fields.items()
    #     if field != "cost"
    # }

    def get_serializer_class(self):
        from .serializers import QuantitativeRiskStudyActionPlanSerializer

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
