"""
URL patterns for Business Continuity API
"""

from django.urls import path, include
from rest_framework import routers

from .views import BCPPlanViewSet

# Create router and register viewsets
router = routers.DefaultRouter()
router.register(r'plans', BCPPlanViewSet, basename='plans')

urlpatterns = [
    path("", include(router.urls)),
]
