from typing import Any, Dict
from datetime import datetime
from integrations.base import BaseFieldMapper


class JiraFieldMapper(BaseFieldMapper):
    """Maps fields between AppliedControl and Jira issues"""

    # Field mappings: local_field -> jira_field
    FIELD_MAPPINGS = {
        "name": "summary",
        "description": "description",
        "status": "status",
        "priority": "priority",
        "eta": "duedate",
        "start_date": "customfield_10015",  # Example: Sprint start date custom field
    }

    # Status mappings
    STATUS_MAP_TO_JIRA = {
        "to_do": "To Do",
        "in_progress": "In Progress",
        "on_hold": "On Hold",
        "active": "Done",
        "deprecated": "Closed",
        "--": "To Do",
    }

    STATUS_MAP_FROM_JIRA = {
        "To Do": "to_do",
        "In Progress": "in_progress",
        "On Hold": "on_hold",
        "Done": "active",
        "Closed": "deprecated",
    }

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

    def _transform_value_to_remote(self, field: str, value: Any) -> Any:
        """Transform AppliedControl field values to Jira format"""
        if value is None:
            return None

        if field == "status":
            # Jira expects status as object with name
            jira_status = self.STATUS_MAP_TO_JIRA.get(value, "To Do")
            return {"name": jira_status}

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
            # Jira uses Atlassian Document Format (ADF) or Wiki markup
            # For simplicity, we'll use plain text wrapped in ADF
            return {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": value or ""}],
                    }
                ],
            }

        return value

    def _transform_value_to_local(self, field: str, value: Any) -> Any:
        """Transform Jira field values to AppliedControl format"""
        if value is None:
            return None

        if field == "status":
            # Extract status name from Jira object
            if isinstance(value, dict):
                status_name = value.get("name", "")
            else:
                status_name = str(value)
            return self.STATUS_MAP_FROM_JIRA.get(status_name, "to_do")

        elif field == "priority":
            # Extract priority name from Jira object
            if isinstance(value, dict):
                priority_name = value.get("name", "Medium")
            else:
                priority_name = str(value)
            return self.PRIORITY_MAP_FROM_JIRA.get(priority_name, 3)

        elif field in ["eta", "start_date"]:
            # Parse date string to date object
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
                except:
                    return None
            return value

        elif field == "description":
            # Extract text from ADF format
            if isinstance(value, dict) and value.get("type") == "doc":
                # Simple text extraction from ADF
                text_parts = []
                for content in value.get("content", []):
                    if content.get("type") == "paragraph":
                        for item in content.get("content", []):
                            if item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                return "\n".join(text_parts)
            return str(value) if value else ""

        return value
