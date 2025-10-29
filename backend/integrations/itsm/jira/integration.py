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
        "required": ["project_key"],
        "properties": {
            "project_key": {"type": "string", "description": "Jira project key"},
            "issue_type": {"type": "string", "default": "Task"},
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

    def _get_mapper(self) -> BaseFieldMapper:
        """
        Create a JiraFieldMapper instance configured for this orchestrator.
        
        Returns:
            BaseFieldMapper: A `JiraFieldMapper` initialized with the orchestrator's configuration.
        """
        return JiraFieldMapper(self.configuration)

    def _get_client(self) -> JiraClient:
        """
        Create a JiraClient configured with the orchestrator's current configuration.
        
        Returns:
            JiraClient: A Jira client instance initialized with this orchestrator's configuration.
        """
        return JiraClient(self.configuration)

    def _extract_remote_id(self, payload: Dict[str, Any]) -> str:
        """
        Extract the Jira issue key from a webhook payload.
        
        Parameters:
            payload (Dict[str, Any]): Webhook payload from Jira; may contain an "issue" object with a "key" field.
        
        Returns:
            str | None: The Jira issue key (e.g., "PROJ-123") if present in the payload, otherwise `None`.
        """
        # Jira webhook structure: { "issue": { "key": "PROJ-123", ... } }
        if "issue" in payload:
            return payload["issue"].get("key")
        return payload.get("key")

    def _extract_remote_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts Jira issue data from a webhook payload.
        
        Returns:
            A dictionary with keys `key`, `fields`, and `updated` when the payload contains an `issue` entry; otherwise returns the original `payload`.
        """
        if "issue" in payload:
            issue = payload["issue"]
            return {
                "key": issue.get("key"),
                "fields": issue.get("fields", {}),
                "updated": issue.get("fields", {}).get("updated"),
            }
        return payload

    def handle_webhook_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """
        Process a Jira webhook event and perform the corresponding synchronization action.
        
        Handles Jira issue lifecycle events: logs and acknowledges created issues, pulls and applies changes for updated issues, and handles remote deletions for deleted issues. Unrecognized event types are not handled.
        
        Parameters:
            event_type (str): The webhook event identifier (e.g., contains "issue_created", "issue_updated", or "issue_deleted").
            payload (Dict[str, Any]): The webhook payload. The issue key is expected at payload["issue"]["key"] or at payload["key"] for some event shapes.
        
        Returns:
            bool: `True` if the event was recognized and handled, `False` otherwise.
        """
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