"""
URL patterns for Third Party Management API
"""

from django.urls import path, include
from rest_framework import routers

from .views import ThirdPartyEntityViewSet

# Create router and register viewsets
router = routers.DefaultRouter()
router.register(r'entities', ThirdPartyEntityViewSet, basename='entities')

urlpatterns = [
    path("", include(router.urls)),
]
