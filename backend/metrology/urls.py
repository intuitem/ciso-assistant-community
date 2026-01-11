from django.urls import path
from rest_framework import routers

from metrology.views import (
    MetricDefinitionViewSet,
    MetricInstanceViewSet,
    CustomMetricSampleViewSet,
    BuiltinMetricSampleViewSet,
    DashboardViewSet,
    DashboardWidgetViewSet,
)

router = routers.DefaultRouter()
router.register(
    r"metric-definitions", MetricDefinitionViewSet, basename="metric-definitions"
)
router.register(r"metric-instances", MetricInstanceViewSet, basename="metric-instances")
router.register(
    r"custom-metric-samples",
    CustomMetricSampleViewSet,
    basename="custom-metric-samples",
)
router.register(
    r"builtin-metric-samples",
    BuiltinMetricSampleViewSet,
    basename="builtin-metric-samples",
)
router.register(r"dashboards", DashboardViewSet, basename="dashboards")
router.register(
    r"dashboard-widgets", DashboardWidgetViewSet, basename="dashboard-widgets"
)

urlpatterns = router.urls
