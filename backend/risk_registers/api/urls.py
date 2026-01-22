"""
URL patterns for Risk Registers API
"""

from django.urls import path, include
from rest_framework import routers

from .views import (
    AssetRiskViewSet,
    RiskRegisterViewSet,
    RiskReportingViewSet
)

# Create router and register viewsets
router = routers.DefaultRouter()
router.register(r'asset-risks', AssetRiskViewSet, basename='asset-risks')
router.register(r'registers', RiskRegisterViewSet, basename='registers')
router.register(r'reporting', RiskReportingViewSet, basename='reporting')

urlpatterns = [
    path("", include(router.urls)),
]
