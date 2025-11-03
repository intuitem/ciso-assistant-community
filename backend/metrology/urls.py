from django.urls import path
from rest_framework import routers

from metrology.views import (
    MetricDefinitionViewSet,
    MetricInstanceViewSet,
    MetricSampleViewSet,
)

router = routers.DefaultRouter()
router.register(
    r"metric-definitions", MetricDefinitionViewSet, basename="metric-definitions"
)
router.register(r"metric-instances", MetricInstanceViewSet, basename="metric-instances")
router.register(r"metric-samples", MetricSampleViewSet, basename="metric-samples")

urlpatterns = router.urls
