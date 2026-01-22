"""
URL patterns for Privacy API
"""

from django.urls import path, include
from rest_framework import routers

from .views import DataAssetViewSet, ConsentRecordViewSet, DataSubjectRightViewSet

# Create router and register viewsets
router = routers.DefaultRouter()
router.register(r'data-assets', DataAssetViewSet, basename='data-assets')
router.register(r'consent-records', ConsentRecordViewSet, basename='consent-records')
router.register(r'data-subject-rights', DataSubjectRightViewSet, basename='data-subject-rights')

urlpatterns = [
    path("", include(router.urls)),
]
