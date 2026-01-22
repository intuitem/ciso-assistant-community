"""
URL routing for RMF Operations bounded context
"""

from django.urls import path, include
from rest_framework import routers

from .views import (
    SystemGroupViewSet, StigChecklistViewSet,
    VulnerabilityFindingViewSet, ChecklistScoreViewSet,
    NessusScanViewSet, StigTemplateViewSet, ArtifactViewSet
)

# Create router and register viewsets
router = routers.DefaultRouter()
router.register(r'system-groups', SystemGroupViewSet, basename='system-groups')
router.register(r'checklists', StigChecklistViewSet, basename='checklists')
router.register(r'vulnerability-findings', VulnerabilityFindingViewSet, basename='vulnerability-findings')
router.register(r'checklist-scores', ChecklistScoreViewSet, basename='checklist-scores')
router.register(r'nessus-scans', NessusScanViewSet, basename='nessus-scans')
router.register(r'templates', StigTemplateViewSet, basename='templates')
router.register(r'artifacts', ArtifactViewSet, basename='artifacts')

urlpatterns = [
    path("", include(router.urls)),
]