"""
URL Configuration for POAM API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import POAMItemViewSet

router = DefaultRouter()
router.register(r'poam-items', POAMItemViewSet, basename='poam-item')

urlpatterns = [
    path('', include(router.urls)),
]
