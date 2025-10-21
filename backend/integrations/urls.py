from django.urls import path
from . import views

app_name = "integrations"

urlpatterns = [
    # URL format: /api/integrations/webhook/<config_uuid>/?token=<webhook_secret>
    path(
        "webhook/<uuid:config_id>/",
        views.IntegrationWebhookView.as_view(),
        name="webhook-receiver",
    ),
]
