from rest_framework import status
from rest_framework.views import Response
from core.views import BaseModelViewSet as AbstractBaseModelViewSet

from .models import (
    QuantitativeRiskStudy,
    QuantitativeRiskScenario,
    QuantitativeRiskHypothesis,
    QuantitativeRiskAggregation,
)

from rest_framework.decorators import action

import structlog

logger = structlog.get_logger(__name__)


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


class QuantitativeRiskScenarioViewSet(BaseModelViewSet):
    model = QuantitativeRiskScenario
    filterset_fields = [
        "quantitative_risk_study",
        "assets",
        "threats",
        "vulnerabilities",
        "qualifications",
    ]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["-created_at"]


class QuantitativeRiskHypothesisViewSet(BaseModelViewSet):
    model = QuantitativeRiskHypothesis
    filterset_fields = [
        "quantitative_risk_study",
        "quantitative_risk_scenario",
        "quantitative_risk_aggregations",
        "existing_applied_controls",
        "added_applied_controls",
        "removed_applied_controls",
    ]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["post"], url_path="run-simulation")
    def run_simulation(self, request, pk=None):
        """
        Triggers a Monte Carlo simulation for a specific risk hypothesis.
        """
        hypothesis = self.get_object()  # Retrieves the instance based on pk
        sim_size: int = request.data.get("sim_size", 20000)
        write: bool = request.data.get("write", False)

        try:
            results = hypothesis.run_simulation(sim_size=sim_size, write=write)
            return Response(results, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.warning(
                "Validation error during risk hypothesis simulation: %s",
                e,
                exc_info=True,
            )
            return Response(
                {"error": "Invalid input provided."}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred during the simulation."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class QuantitativeRiskAggregationViewSet(BaseModelViewSet):
    model = QuantitativeRiskAggregation
    filterset_fields = [
        "quantitative_risk_study",
    ]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["-created_at"]
