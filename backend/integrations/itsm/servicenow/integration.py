from typing import Any, Dict
from structlog import get_logger
from integrations.base import BaseITSMOrchestrator
from integrations.registry import IntegrationRegistry
from .client import ServiceNowClient
from .mapper import ServiceNowFieldMapper

logger = get_logger(__name__)

SERVICENOW_CONFIG_SCHEMA = {
    "required": ["credentials", "settings"],
    "credentials": {
        "required": ["instance_url", "username", "password"],
        "properties": {
            "instance_url": {
                "type": "string",
                "description": "e.g., https://instance.service-now.com",
            },
            "username": {"type": "string"},
            "password": {"type": "string"},
        },
    },
    "settings": {
        "required": ["table_name"],
        "properties": {
            "table_name": {"type": "string", "default": "incident"},
            "base_query": {"type": "string", "default": "active=true"},
            "enable_incoming_sync": {"type": "boolean", "default": True},
            "enable_outgoing_sync": {"type": "boolean", "default": True},
        },
    },
}


class ServiceNowOrchestrator(BaseITSMOrchestrator):
    client_class = ServiceNowClient
    mapper_class = ServiceNowFieldMapper

    def _get_mapper(self):
        return ServiceNowFieldMapper(self.configuration)

    def _get_client(self):
        return ServiceNowClient(self.configuration)

    def _extract_remote_id(self, payload: Dict[str, Any]) -> str:
        # Assumes ServiceNow Business Rule sends the record as the root json or under 'result'
        # Payload: { "sys_id": "...", "number": "..." }
        return payload.get("sys_id")

    def _extract_remote_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "key": payload.get("sys_id"),
            "fields": payload,  # The payload itself usually contains the fields
            "updated": payload.get("sys_updated_on"),
        }

    def handle_webhook_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        # Define event types in your ServiceNow 'Business Rule' that calls this webhook
        # e.g., 'sn_update', 'sn_delete'
        remote_id = self._extract_remote_id(payload)
        if not remote_id:
            logger.warning(
                f"Could not extract remote ID from payload for event {event_type}"
            )
            return False

        if event_type == "sn_update":
            remote_data = self._extract_remote_data(payload)
            return self.pull_changes(remote_id, remote_data)
        elif event_type == "sn_delete":
            return self._handle_remote_deletion(remote_id)

        return False

    def get_interactive_actions(self):
        return ["get_tables", "get_columns", "get_choices"]

    def execute_action(self, action: str, params: dict):
        client = self._get_client()

        if action == "get_tables":
            return client.get_available_tables()

        elif action == "get_columns":
            table = params.get("table_name")
            if not table:
                raise ValueError("Parameter 'table_name' is required for get_columns")
            return client.get_table_columns(table)

        elif action == "get_choices":
            table = params.get("table_name")
            field = params.get("field_name")
            if not table or not field:
                raise ValueError(
                    "Parameters 'table_name' and 'field_name' are required"
                )
            return client.get_field_choices(table, field)

        else:
            raise NotImplementedError(f"Unknown action: {action}")

    def validate_webhook_request(self, request) -> bool:
        """
        Validates the request by checking for a matching secret token header.
        ServiceNow doesn't support HMAC signing natively easily, so we use a
        shared secret header approach.
        """
        # Define the header we expect from ServiceNow
        # (The user must configure this in their Outbound REST Message)
        incoming_secret = request.headers.get("X-CISO-Secret")

        if not incoming_secret:
            # Fallback: check query params if they prefer that method
            # incoming_secret = request.GET.get("secret")
            pass

        if not incoming_secret:
            raise ValueError("Missing authentication header (X-CISO-Secret)")

        configured_secret = self.configuration.webhook_secret
        if not configured_secret:
            raise ValueError("Webhook secret not configured on server")

        # Constant time comparison to prevent timing attacks
        import hmac

        # Compare strings safely
        if not hmac.compare_digest(incoming_secret, configured_secret):
            raise ValueError("Invalid secret token")

        return True

    def extract_webhook_event_type(self, payload: dict) -> str:
        # Based on the Business Rule script we wrote earlier,
        # we inject an "event" field into the JSON body.
        return payload.get("event")


IntegrationRegistry.register(
    name="servicenow",
    provider_type="itsm",
    client_class=ServiceNowClient,
    mapper_class=ServiceNowFieldMapper,
    orchestrator_class=ServiceNowOrchestrator,
    display_name="ServiceNow",
    description="Sync with ServiceNow Tables (Incident, etc)",
    config_schema=SERVICENOW_CONFIG_SCHEMA,
)
