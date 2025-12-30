from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import WebhookEndpoint, WebhookEventType
from .serializers import WebhookEndpointSerializer
from core.views import BaseModelViewSet


class WebhookEndpointViewSet(BaseModelViewSet):
    """
    API endpoint to create, list, retrieve, update, and delete
    Webhook Endpoints.
    """

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    model = WebhookEndpoint
    ordering_fields = ["is_active", "created_at", "name", "url"]
    ordering = ["-is_active", "-created_at"]

    def get_serializer_class(self, **kwargs):
        return WebhookEndpointSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_queryset(self):
        """
        Users can only see their own webhook endpoints.
        """
        return WebhookEndpoint.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """
        Automatically assign the current user as the owner.
        """
        serializer.save(owner=self.request.user)


class WebhookEventTypeView(APIView):
    """
    A read-only endpoint for the UI to fetch all possible
    event types from the registry.
    """

    def get(self, request, format=None):
        """
        Returns a list of all registered event type strings.
        """
        all_types = WebhookEventType.objects.values_list("name", flat=True).order_by(
            "name"
        )
        return Response(all_types)
