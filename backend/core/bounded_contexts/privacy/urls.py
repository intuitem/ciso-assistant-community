"""
URL configuration for Privacy bounded context API
"""

from django.urls import path, include
from rest_framework import routers
from .views import (
    DataAssetViewSet,
    DataFlowViewSet,
)

router = routers.DefaultRouter()
router.register(r'data-assets', DataAssetViewSet, basename='data-assets')
router.register(r'data-flows', DataFlowViewSet, basename='data-flows')

urlpatterns = [
    path('', include(router.urls)),
]

