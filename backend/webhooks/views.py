from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import WebhookEndpoint, WebhookEventType
from .serializers import WebhookEndpointSerializer
from .registry import webhook_registry


class WebhookEndpointViewSet(viewsets.ModelViewSet):
    """
    API endpoint to create, list, retrieve, update, and delete
    Webhook Endpoints.
    """

    serializer_class = WebhookEndpointSerializer
    permission_classes = [permissions.IsAuthenticated]

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
