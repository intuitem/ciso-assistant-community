from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = "integrations"

router = DefaultRouter()
router.register(
    r"configs",
    views.IntegrationConfigurationViewSet,
    basename="integration-configuration",
)

urlpatterns = [
    path(
        "providers/",
        views.IntegrationProviderListView.as_view(),
        name="provider-list",
    ),
    path(
        "test-connection/",
        views.ConnectionTestView.as_view(),
        name="test-connection",
    ),
    path(
        "webhook/<uuid:config_id>/",
        views.IntegrationWebhookView.as_view(),
        name="webhook-receiver",
    ),
    path(
        "sync-mappings/<uuid:pk>/",
        views.SyncMappingDeleteView.as_view(),
        name="sync-mapping-delete",
    ),
    path("", include(router.urls)),
]
