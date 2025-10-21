from abc import abstractmethod
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views import View

from integrations.models import IntegrationConfiguration
from integrations.tasks import process_webhook_event


class BaseWebhookView(View):
    """Base webhook receiver"""

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, provider_name, config_id):
        # Verify webhook signature
        config = IntegrationConfiguration.objects.get(pk=config_id)

        if not self._verify_signature(request, config):
            return JsonResponse({"error": "Invalid signature"}, status=403)

        # Parse payload
        payload = json.loads(request.body)
        event_type = self._extract_event_type(request, payload)

        # Queue async processing
        process_webhook_event.schedule(args=(config_id, event_type, payload))

        return JsonResponse({"status": "accepted"}, status=202)

    @abstractmethod
    def _verify_signature(self, request, config):
        """Provider-specific signature verification"""
        pass

    @abstractmethod
    def _extract_event_type(self, request, payload):
        """Extract event type from webhook"""
        pass
