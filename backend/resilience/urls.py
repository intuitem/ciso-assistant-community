from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    BusinessImpactAnalysisViewSet,
    AssetAssessmentViewSet,
    EscalationThresholdViewSet,
    DoraIncidentReportViewSet,
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

router.register(
    r"dora-incident-reports",
    DoraIncidentReportViewSet,
    basename="dora-incident-reports",
)

urlpatterns = [
    path("", include(router.urls)),
]
