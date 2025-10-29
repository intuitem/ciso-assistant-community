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

    # Field thats can be pulled/pushed and their associated operations
    # E.g. an applied control's name will be pulled from Jira on create only,
    # for update operations, the applied control will retail its name.
    # However, its status will be pulled on both create and update operations.
    FIELD_MAPPINGS_OPERATIONS = {
        "name": {"pull": {"create"}, "push": {"create", "update"}},
        "description": {"pull": {"create"}, "push": {"create", "update"}},
        "status": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "priority": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "eta": {"pull": {"create", "update"}, "push": {"create", "update"}},
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

    def get_allowed_fields(self, direction: str, operation: str) -> set[str]:
        """
        Return the set of local field names allowed for the given synchronization direction and operation.
        
        Parameters:
            direction (str): Sync direction, either "pull" or "push".
            operation (str): Operation type, typically "create" or "update".
        
        Returns:
            allowed_fields (set[str]): Set of local field keys permitted for the specified direction and operation.
        """
        allowed = set()
        for field, ops in self.FIELD_MAPPINGS_OPERATIONS.items():
            if operation in ops.get(direction, set()):
                allowed.add(field)
        return allowed

    def to_remote(self, local_object: models.Model) -> dict[str, Any]:
        """
        Map a local model instance into a Jira-compatible payload for creating an issue.
        
        Parameters:
        	local_object (models.Model): Local model instance to convert.
        
        Returns:
        	remote_data (dict[str, Any]): Mapping of Jira field keys (with the "fields." prefix removed) to transformed values ready for a create request.
        """
        allowed_fields = self.get_allowed_fields("push", "create")
        remote_data = {}
        for local_field, remote_field in self._get_mappings().items():
            if local_field in allowed_fields:
                value = self._get_local_value(local_object, local_field)
                if value is not None:
                    transformed = self._transform_value_to_remote(local_field, value)
                    if transformed is not None:
                        remote_data[remote_field] = transformed
        return self._strip_fields_prefix(remote_data)

    def to_remote_partial(
        self, local_object: models.Model, changed_fields: list[str]
    ) -> dict[str, Any]:
        """
        Convert a subset of a local object's changed fields into a Jira-compatible remote payload.
        
        Parameters:
            local_object (models.Model): The local model instance containing current values.
            changed_fields (list[str]): Local field names that have changed and should be considered for conversion.
        
        Returns:
            dict[str, Any]: A mapping of remote field keys (with the "fields." prefix removed) to converted values for update.
        """
        allowed_fields = self.get_allowed_fields("push", "update")
        fields_to_convert = [f for f in changed_fields if f in allowed_fields]
        remote_data_nested = super().to_remote_partial(local_object, fields_to_convert)
        return self._strip_fields_prefix(remote_data_nested)

    def to_local(self, remote_data: dict[str, Any]) -> dict[str, Any]:
        """
        Map Jira remote data into local field values for update operations.
        
        Parameters:
            remote_data (dict[str, Any]): Raw Jira issue payload.
        
        Returns:
            dict[str, Any]: A mapping of local field names to transformed values containing only fields allowed for pull/update.
        """
        allowed_fields = self.get_allowed_fields("pull", "update")
        local_data = super().to_local(remote_data)
        return {k: v for k, v in local_data.items() if k in allowed_fields}

    def _strip_fields_prefix(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Remove the "fields." prefix from dictionary keys.
        
        Parameters:
            data (dict[str, Any]): Mapping of remote keys that may include the "fields." prefix.
        
        Returns:
            dict[str, Any]: A new dictionary where keys that started with "fields." have that prefix removed; all other keys are preserved unchanged.
        """
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
        """
        Convert a local field value into the representation Jira expects for that field.
        
        Behavior:
        - `status`: maps a local status key to a Jira status name (string).
        - `priority`: maps a local numeric priority to `{"name": "<JiraPriority>"}`.
        - `eta` / `start_date`: returns a date string in YYYY-MM-DD format when possible.
        - `description`: returns an Atlassian Document Format (ADF) document dict with the value as a single paragraph.
        - other fields: returned unchanged.
        
        Parameters:
            field (str): Local field name.
            value (Any): Local field value to convert.
        
        Returns:
            Any: The value converted to the Jira-expected representation for `field`.
        """
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

        elif field == "description":
            # Convert to Atlassian Document Format (ADF)
            return {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": str(value),
                            }
                        ],
                    }
                ],
            }

        return value

    def _transform_value_to_local(self, field: str, value: Any) -> Any:
        """
        Convert a Jira field value into the corresponding AppliedControl representation.
        
        Parameters:
            field (str): The local field name being populated (e.g., "status", "priority", "eta", "start_date", "description").
            value (Any): The raw value extracted from Jira (already keyed from `fields.*`), which may be a dict, string, date/datetime, or None.
        
        Returns:
            Any: The value converted to the AppliedControl format for the given field (e.g., local status key, numeric priority, Python date, plain-text description),
            or `None` when the Jira value is absent or cannot be mapped/parsed.
        """
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