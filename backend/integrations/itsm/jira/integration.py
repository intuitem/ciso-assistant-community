"""
Jira integration implementation

This module registers the Jira integration with the IntegrationRegistry.
It will be automatically discovered and loaded on Django startup.
"""

from typing import Any, Dict

from structlog import get_logger

from integrations.base import BaseFieldMapper, BaseITSMOrchestrator
from integrations.registry import IntegrationRegistry

from .client import JiraClient
from .mapper import JiraFieldMapper

import hashlib
import hmac

logger = get_logger(__name__)


# Configuration schema for Jira integration
JIRA_CONFIG_SCHEMA = {
    "required": ["credentials", "settings"],
    "credentials": {
        "required": ["server_url", "email", "api_token"],
        "properties": {
            "server_url": {"type": "string", "description": "Jira server URL"},
            "email": {"type": "string", "description": "Jira user email"},
            "api_token": {
                "type": "string",
                "description": "Jira API token",
            },
        },
    },
    "settings": {
        "required": ["table_name"],
        "properties": {
            # Composite "<PROJECT_KEY>:<Issue Type Name>" string the
            # FieldMapper UI writes back. Falls back to the legacy split
            # ``project_key`` / ``issue_type`` settings for backward compat.
            "table_name": {
                "type": "string",
                "description": "Composite project key and issue type, e.g. 'PROJ:Task'",
            },
            "project_key": {"type": "string", "description": "Jira project key"},
            "issue_type": {"type": "string", "default": "Task"},
            "field_map": {
                "type": "object",
                "description": "Map of CISO Assistant fields to Jira field IDs",
            },
            "value_map": {
                "type": "object",
                "description": "Map of CISO Assistant choice values to Jira choice values, keyed by field",
            },
            "enable_incoming_sync": {"type": "boolean", "default": True},
            "enable_outgoing_sync": {"type": "boolean", "default": True},
            "sync_comments": {"type": "boolean", "default": True},
            "sync_attachments": {"type": "boolean", "default": False},
        },
    },
}


class JiraOrchestrator(BaseITSMOrchestrator):
    """Orchestrates sync operations between AppliedControl and Jira"""

    # Required class attributes for registry decorator
    client_class = JiraClient
    mapper_class = JiraFieldMapper

    def _get_mapper(self, model_key="applied_control") -> BaseFieldMapper:
        return JiraFieldMapper(self.configuration, model_key)

    def _get_client(self, model_key="applied_control") -> JiraClient:
        return JiraClient(self.configuration, model_key)

    def _extract_remote_id(self, payload: Dict[str, Any]) -> str:
        """Extract issue key from Jira webhook payload"""
        # Jira webhook structure: { "issue": { "key": "PROJ-123", ... } }
        if "issue" in payload:
            return payload["issue"].get("key")
        return payload.get("key", "")

    def _extract_remote_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract issue data from Jira webhook payload"""
        if "issue" in payload:
            issue = payload["issue"]
            return {
                "key": issue.get("key"),
                "fields": issue.get("fields", {}),
                "updated": issue.get("fields", {}).get("updated"),
            }
        return payload

    def handle_webhook_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Handle Jira-specific webhook events"""
        # Jira webhook event types

        if "issue_created" in event_type:
            # NOTE: For now, we don't create local objects from Jira
            # This could be implemented if needed
            logger.info("Jira issue created", key=payload.get("issue", {}).get("key"))
            return True

        elif "issue_updated" in event_type:
            logger.info(
                "Updating Jira issue from webhook event",
                webhook_event=event_type,
                id=payload.get("issue", {}).get("key"),
            )
            remote_id = self._extract_remote_id(payload)
            remote_data = self._extract_remote_data(payload)
            return self.pull_changes(remote_id, remote_data)

        elif "issue_deleted" in event_type:
            remote_id = self._extract_remote_id(payload)
            return self._handle_remote_deletion(remote_id)

        else:
            logger.warning(f"Unknown Jira webhook event: {event_type}")
            return False

    def validate_webhook_request(self, request) -> bool:
        signature_header = request.headers.get("X-Hub-Signature")
        if not signature_header:
            raise ValueError("Missing X-Hub-Signature header")

        if not self.configuration.webhook_secret:
            raise ValueError("Webhook secret not configured on server")

        try:
            method, provided_signature = signature_header.split("=", 1)
        except ValueError:
            raise ValueError("Invalid signature header format")

        if method.lower() != "sha256":
            raise ValueError("Unsupported signature method")

        expected_signature = hmac.new(
            self.configuration.webhook_secret.encode("utf-8"),
            request.body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(provided_signature, expected_signature)

    def extract_webhook_event_type(self, payload: dict) -> str:
        return payload.get("webhookEvent")

    def get_interactive_actions(self):
        return ["get_tables", "get_columns", "get_choices", "suggest_mapping"]

    def execute_action(self, action: str, params: dict):
        model_key = params.get("model_key", self.DEFAULT_MODEL_KEY)
        client = self.client_for(model_key)

        if action == "get_tables":
            return client.get_available_tables()

        if action == "get_columns":
            table = params.get("table_name")
            if not table:
                raise ValueError("Parameter 'table_name' is required for get_columns")
            return client.get_table_columns(table)

        if action == "get_choices":
            table = params.get("table_name")
            field = params.get("field_name")
            if not table or not field:
                raise ValueError(
                    "Parameters 'table_name' and 'field_name' are required"
                )
            return client.get_field_choices(table, field)

        if action == "suggest_mapping":
            table = params.get("table_name")
            if not table:
                raise ValueError(
                    "Parameter 'table_name' is required for suggest_mapping"
                )
            return self.mapper_for(model_key).suggest_mapping_for_table(table, client)

        raise NotImplementedError(f"Unknown action: {action}")


# Register the Jira integration
IntegrationRegistry.register(
    name="jira",
    provider_type="itsm",
    client_class=JiraClient,
    mapper_class=JiraFieldMapper,
    orchestrator_class=JiraOrchestrator,
    display_name="Jira",
    description="Atlassian Jira integration for ITSM ticket synchronization",
    config_schema=JIRA_CONFIG_SCHEMA,
)

logger.info("Jira integration registered")
