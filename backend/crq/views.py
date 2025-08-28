from rest_framework import status
from rest_framework.views import Response
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .models import (
    QuantitativeRiskStudy,
    QuantitativeRiskScenario,
    QuantitativeRiskHypothesis,
)

from rest_framework.decorators import action

import structlog

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


class QuantitativeRiskHypothesisViewSet(BaseModelViewSet):
    model = QuantitativeRiskHypothesis
    filterset_fields = [
        "quantitative_risk_scenario",
        "risk_stage",
    ]
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

    @action(detail=True, methods=["post"], url_path="run-simulation")
    def run_simulation(self, request, pk=None):
        """
        Triggers a Monte Carlo simulation for a specific risk hypothesis.
        """
        hypothesis = self.get_object()
        return Response({})
