"""
URL configuration for SecurityOperations bounded context API
"""

from django.urls import path, include
from rest_framework import routers
from .views import (
    SecurityIncidentViewSet,
    AwarenessProgramViewSet,
    AwarenessCampaignViewSet,
    AwarenessCompletionViewSet,
)

router = routers.DefaultRouter()
router.register(r'security-incidents', SecurityIncidentViewSet, basename='security-incidents')
router.register(r'awareness-programs', AwarenessProgramViewSet, basename='awareness-programs')
router.register(r'awareness-campaigns', AwarenessCampaignViewSet, basename='awareness-campaigns')
router.register(r'awareness-completions', AwarenessCompletionViewSet, basename='awareness-completions')

urlpatterns = [
    path('', include(router.urls)),
]

