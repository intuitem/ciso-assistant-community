from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    BusinessImpactAnalysisViewSet,
    AssetAssessmentViewSet,
    EscalationThresholdViewSet,
)

router = DefaultRouter()
router.register(
    r"business-impact-analysis",
    BusinessImpactAnalysisViewSet,
    basename="business-impact-analysis",
)
router.register(
    r"asset-assessments", AssetAssessmentViewSet, basename="asset-assessments"
)
router.register(
    r"escalation-thresholds",
    EscalationThresholdViewSet,
    basename="escalation-thresholds",
)

urlpatterns = [
    path("", include(router.urls)),
]
