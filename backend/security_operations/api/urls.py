"""
URL patterns for Security Operations API
"""

from django.urls import path, include
from rest_framework import routers

from .views import SecurityIncidentViewSet

# Create router and register viewsets
router = routers.DefaultRouter()
router.register(r'incidents', SecurityIncidentViewSet, basename='incidents')

urlpatterns = [
    path("", include(router.urls)),
]
