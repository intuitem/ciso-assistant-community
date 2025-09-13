from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    QuantitativeRiskHypothesisViewSet,
    QuantitativeRiskScenarioViewSet,
    QuantitativeRiskStudyViewSet,
    QuantitativeRiskStudyActionPlanList,
)

router = DefaultRouter()
router.register(
    "quantitative-risk-studies",
    QuantitativeRiskStudyViewSet,
    basename="quantitative-risk-studies",
)
router.register(
    "quantitative-risk-scenarios",
    QuantitativeRiskScenarioViewSet,
    basename="quantitative-risk-scenarios",
)
router.register(
    "quantitative-risk-hypotheses",
    QuantitativeRiskHypothesisViewSet,
    basename="quantitative-risk-hypotheses",
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "quantitative-risk-studies/<uuid:pk>/action-plan/",
        QuantitativeRiskStudyActionPlanList.as_view(),
        name="quantitative-risk-study-action-plan",
    ),
]
