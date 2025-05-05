from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import filters
from django.db.models import Count
from itertools import chain
from collections import defaultdict

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.core.cache import cache

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


class AssetAssessmentViewSet(BaseModelViewSet):
    model = AssetAssessment


class EscalationThresholdViewSet(BaseModelViewSet):
    model = EscalationThreshold
