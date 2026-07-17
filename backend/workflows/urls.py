from django.urls import include, path
from rest_framework.routers import DefaultRouter

from workflows.views import (
    WorkflowInstanceViewSet,
    WorkflowScheduleViewSet,
    WorkflowSecretViewSet,
    WorkflowVersionViewSet,
    WorkflowViewSet,
    WorkflowWebhookView,
)

router = DefaultRouter()
router.register("workflows", WorkflowViewSet, basename="workflows")
router.register(
    "workflow-versions", WorkflowVersionViewSet, basename="workflow-versions"
)
router.register(
    "workflow-instances", WorkflowInstanceViewSet, basename="workflow-instances"
)
router.register("workflow-secrets", WorkflowSecretViewSet, basename="workflow-secrets")
router.register(
    "workflow-schedules", WorkflowScheduleViewSet, basename="workflow-schedules"
)

urlpatterns = [
    path(
        "hooks/<uuid:workflow_id>/<str:secret>/",
        WorkflowWebhookView.as_view(),
        name="workflow-webhook",
    ),
    path("", include(router.urls)),
]
