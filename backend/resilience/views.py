from os import name
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from core.serializers import RiskMatrixReadSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

SHORT_CACHE_TTL = 2  # mn
MED_CACHE_TTL = 5  # mn
LONG_CACHE_TTL = 60  # mn

from .models import (
    BusinessImpactAnalysis,
    AssetAssessment,
    EscalationThreshold,
)


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "resilience.serializers"


class BusinessImpactAnalysisViewSet(BaseModelViewSet):
    model = BusinessImpactAnalysis
    filterset_fields = [
        "perimeter",
        "perimeter__folder",
        "authors",
        "risk_matrix",
        "status",
    ]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(BusinessImpactAnalysis.Status.choices))

    @action(detail=True, name="Get the BIA metrics")
    def metrics(self, request, pk):
        bia = self.get_object()
        return Response(bia.metrics())

    @action(detail=True, name="Build qualitative table", url_path="build-table")
    def impact_table(self, request, pk):
        bia = self.get_object()
        table = bia.build_table()
        return Response(table)


class AssetAssessmentViewSet(BaseModelViewSet):
    model = AssetAssessment
    filterset_fields = ["bia", "asset"]
    search_fields = ["bia__name", "asset__name"]
    ordering = ["asset"]

    @action(detail=True, name="Get risk matrix", url_path="risk-matrix")
    def risk_matrix(self, request, pk=None):
        aa = self.get_object()
        return Response(RiskMatrixReadSerializer(aa.bia.risk_matrix).data)

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=True, name="Get impact choices")
    def quali_impact(self, request, pk):
        aa = self.get_object()
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [x["name"] for x in aa.bia.parsed_matrix["impact"]],
            )
        )
        choices = undefined | _choices
        return Response(choices)

    @action(detail=True, name="Get the asset assessment details")
    def metrics(self, request, pk):
        res = self.get_object().metrics()
        return Response(res)


class EscalationThresholdViewSet(BaseModelViewSet):
    model = EscalationThreshold
    filterset_fields = ["asset_assessment", "quali_impact"]
    ordering = ["point_in_time"]

    @action(detail=True, name="Get risk matrix", url_path="risk-matrix")
    def risk_matrix(self, request, pk=None):
        et = self.get_object()
        return Response(RiskMatrixReadSerializer(et.risk_matrix).data)

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get quantification units")
    def quant_unit(self, request):
        return Response(dict(EscalationThreshold.QUANT_IMPACT_UNIT))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=True, name="Get impact choices")
    def quali_impact(self, request, pk):
        escalation_threshold = self.get_object()
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [x["name"] for x in escalation_threshold.parsed_matrix["impact"]],
            )
        )
        choices = undefined | _choices
        return Response(choices)
