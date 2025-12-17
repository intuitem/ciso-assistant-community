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

        if event_type == "sn_update":
            remote_data = self._extract_remote_data(payload)
            return self.pull_changes(remote_id, remote_data)
        elif event_type == "sn_delete":
            return self._handle_remote_deletion(remote_id)

        return False


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
