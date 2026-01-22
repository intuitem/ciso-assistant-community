"""
URL configuration for Control Library bounded context API
"""

from django.urls import path, include
from rest_framework import routers
from .views import (
    ControlViewSet,
    PolicyViewSet,
    EvidenceItemViewSet,
    ControlImplementationViewSet,
    PolicyAcknowledgementViewSet,
)

router = routers.DefaultRouter()
router.register(r'controls', ControlViewSet, basename='controls')
router.register(r'policies', PolicyViewSet, basename='policies')
router.register(r'evidence-items', EvidenceItemViewSet, basename='evidence-items')
router.register(r'control-implementations', ControlImplementationViewSet, basename='control-implementations')
router.register(r'policy-acknowledgements', PolicyAcknowledgementViewSet, basename='policy-acknowledgements')

urlpatterns = [
    path('', include(router.urls)),
]

