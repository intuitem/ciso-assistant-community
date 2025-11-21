from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import WebhookEndpointViewSet, WebhookEventTypeView

router = DefaultRouter()
router.register(
    r"endpoints",
    WebhookEndpointViewSet,
    basename="webhook-endpoints",
)

urlpatterns = [
    path("", include(router.urls)),
    path("event-types/", WebhookEventTypeView.as_view(), name="webhook-event-types"),
]
