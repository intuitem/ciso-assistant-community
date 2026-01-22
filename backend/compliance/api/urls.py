"""
URL patterns for Compliance API
"""

from django.urls import path, include
from rest_framework import routers

from .views import (
    ComplianceAssessmentViewSet,
    RequirementAssessmentViewSet,
    ComplianceFindingViewSet,
    ComplianceExceptionViewSet
)

# Create router and register viewsets
router = routers.DefaultRouter()
router.register(r'assessments', ComplianceAssessmentViewSet, basename='assessments')
router.register(r'requirement-assessments', RequirementAssessmentViewSet, basename='requirement-assessments')
router.register(r'findings', ComplianceFindingViewSet, basename='findings')
router.register(r'exceptions', ComplianceExceptionViewSet, basename='exceptions')

urlpatterns = [
    path("", include(router.urls)),
]
