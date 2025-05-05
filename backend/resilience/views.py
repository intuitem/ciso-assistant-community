from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import filters
from django.db.models import Count
from itertools import chain
from collections import defaultdict

from .models import (
    BusinessImpactAnalysis,
    AssetAssessment,
    EscalationThreshold,
)


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "resilience.serializers"


class BusinessImpactAnalysisViewSet(BaseModelViewSet):
    model = BusinessImpactAnalysis


class AssetAssessmentViewSet(BaseModelViewSet):
    model = AssetAssessment


class EscalationThresholdViewSet(BaseModelViewSet):
    model = EscalationThreshold
