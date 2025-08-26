from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    QuantitativeRiskAggregationViewSet,
    QuantitativeRiskHypothesisViewSet,
    QuantitativeRiskScenarioViewSet,
    QuantitativeRiskStudyViewSet,
)

router = DefaultRouter()
router.register(
    "studies", QuantitativeRiskStudyViewSet, basename="quantitative-risk-study"
)
router.register(
    "risk-scenarios",
    QuantitativeRiskScenarioViewSet,
    basename="quantitative-risk-scenario",
)
router.register(
    "hypotheses",
    QuantitativeRiskHypothesisViewSet,
    basename="quantitative-risk-hypothesis",
)
router.register(
    "aggregations",
    QuantitativeRiskAggregationViewSet,
    basename="quantitative-risk-aggregation",
)

urlpatterns = [
    path("", include(router.urls)),
]
