"""
URL configuration for Risk Registers bounded context API
"""

from django.urls import path, include
from rest_framework import routers
from .views import (
    AssetRiskViewSet,
    ThirdPartyRiskViewSet,
    BusinessRiskViewSet,
    RiskTreatmentPlanViewSet,
    RiskExceptionViewSet,
)

router = routers.DefaultRouter()
router.register(r'asset-risks', AssetRiskViewSet, basename='asset-risks')
router.register(r'third-party-risks', ThirdPartyRiskViewSet, basename='third-party-risks')
router.register(r'business-risks', BusinessRiskViewSet, basename='business-risks')
router.register(r'risk-treatment-plans', RiskTreatmentPlanViewSet, basename='risk-treatment-plans')
router.register(r'risk-exceptions', RiskExceptionViewSet, basename='risk-exceptions')

urlpatterns = [
    path('', include(router.urls)),
]

