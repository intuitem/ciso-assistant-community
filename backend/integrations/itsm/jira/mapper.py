from datetime import date, datetime
from typing import Any

import structlog
from django.db import models

from integrations.base import BaseFieldMapper

logger = structlog.get_logger(__name__)


class JiraFieldMapper(BaseFieldMapper):
    """Maps fields between AppliedControl and Jira issues"""

    # Field mappings: local_field -> jira_field
    FIELD_MAPPINGS = {
        "name": "fields.summary",
        "description": "fields.description",
        "status": "fields.status",  # Used by to_local and identified by update_remote_object
        "priority": "fields.priority",
        "eta": "fields.duedate",
    }

    # Status mappings

    STATUS_MAP_FROM_JIRA = {
        "To Do": "to_do",
        "In Progress": "in_progress",
        "On Hold": "on_hold",
        "Active": "active",
        "Closed": "deprecated",
    }
    STATUS_MAP_TO_JIRA = {v: k for k, v in STATUS_MAP_FROM_JIRA.items()}

    # Priority mappings (AppliedControl uses 1-4, Jira uses names)
    PRIORITY_MAP_TO_JIRA = {
        1: "Highest",
        2: "High",
        3: "Medium",
        4: "Low",
    }

    PRIORITY_MAP_FROM_JIRA = {
        "Highest": 1,
        "High": 2,
        "Medium": 3,
        "Low": 4,
        "Lowest": 4,
    }

    def to_remote(self, local_object: models.Model) -> dict[str, Any]:
        """Convert local object to remote format, stripping 'fields.' prefix."""
        remote_data_nested = super().to_remote(local_object)
        return self._strip_fields_prefix(remote_data_nested)

    def to_remote_partial(
        self, local_object: models.Model, changed_fields: list[str]
    ) -> dict[str, Any]:
        """Convert changed fields to remote format, stripping 'fields.' prefix."""
        remote_data_nested = super().to_remote_partial(local_object, changed_fields)
        return self._strip_fields_prefix(remote_data_nested)

    def _strip_fields_prefix(self, data: dict[str, Any]) -> dict[str, Any]:
        """Helper to remove 'fields.' prefix from keys for outgoing updates."""
        stripped_data = {}
        for remote_key, value in data.items():
            if remote_key.startswith("fields."):
                stripped_key = remote_key.split(".", 1)[1]
                stripped_data[stripped_key] = value
            else:
                # Keep keys that don't start with 'fields.' (e.g., 'status' itself)
                stripped_data[remote_key] = value
        return stripped_data

    def _transform_value_to_remote(self, field: str, value: Any) -> Any:
        """Transform AppliedControl field values to Jira format"""
        if value is None:
            return None

        if field == "status":
            # Jira expects status as object with name
            jira_status = self.STATUS_MAP_TO_JIRA.get(value, "To Do")
            return jira_status

        elif field == "priority":
            # Jira expects priority as object with name
            jira_priority = self.PRIORITY_MAP_TO_JIRA.get(value, "Medium")
            return {"name": jira_priority}

        elif field in ["eta", "start_date"]:
            # Jira expects dates in YYYY-MM-DD format
            if isinstance(value, datetime):
                return value.date().isoformat()
            elif hasattr(value, "isoformat"):
                return value.isoformat()
            return str(value)

        return value

    def _transform_value_to_local(self, field: str, value: Any) -> Any:
        """Transform incoming Jira field values to AppliedControl format"""
        # Value is already extracted based on FIELD_MAPPINGS (e.g., value = remote_data['fields']['status'])

        if value is None:
            return None  # Skip if the field is null in Jira

        if field == "status":
            # Value is the Jira status object: {'name': 'In Progress', ...}
            if isinstance(value, dict):
                status_name = value.get("name")
                local_status = self.STATUS_MAP_FROM_JIRA.get(status_name)
                if local_status:
                    return local_status
                else:
                    logger.warning(f"Unmapped Jira status received: '{status_name}'")
                    # Decide on fallback: return None, 'to_do', or keep original?
                    return None  # Or maybe AppliedControl.Status.UNDEFINED?
            else:
                logger.warning(f"Received non-dict value for status: {value}")
                return None

        elif field == "priority":
            # Value is the Jira priority object: {'name': 'High', ...}
            if isinstance(value, dict):
                priority_name = value.get("name")
                local_priority = self.PRIORITY_MAP_FROM_JIRA.get(priority_name)
                if (
                    local_priority is not None
                ):  # Check explicitly for None, as 0 could be valid elsewhere
                    return local_priority
                else:
                    logger.warning(
                        f"Unmapped Jira priority received: '{priority_name}'"
                    )
                    return None  # Or a default like 3?
            else:
                logger.warning(f"Received non-dict value for priority: {value}")
                return None

        elif field in ["eta", "start_date"]:
            # Value is a date string 'YYYY-MM-DD' or datetime string
            if isinstance(value, str):
                try:
                    # Try parsing just the date part first
                    return date.fromisoformat(value[:10])
                except ValueError:
                    try:  # Fallback to datetime parsing if needed
                        # Handle timezone info if present
                        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        return dt.date()
                    except ValueError:
                        logger.warning(
                            f"Could not parse date string from Jira: {value}"
                        )
                        return None
            elif isinstance(
                value, (datetime, date)
            ):  # Should ideally be string, but handle just in case
                return value.date() if isinstance(value, datetime) else value
            else:
                logger.warning(
                    f"Received non-string/non-datetime value for date field {field}: {value}"
                )
                return None

        elif field == "description":
            # Handle both ADF and plain text from Jira
            if isinstance(value, dict) and value.get("type") == "doc":
                # Simple text extraction from ADF
                text_parts = []
                for content in value.get("content", []):
                    if content.get("type") == "paragraph":
                        for item in content.get("content", []):
                            if item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                return "\n".join(text_parts).strip()  # Join paragraphs
            elif isinstance(value, str):
                # It's already plain text
                return value.strip()
            else:
                # Unexpected format
                logger.warning(
                    f"Received unexpected format for description: {type(value)}"
                )
                return str(value) if value else ""  # Best effort string conversion

        return value
