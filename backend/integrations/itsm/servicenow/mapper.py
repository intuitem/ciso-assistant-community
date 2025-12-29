from datetime import datetime, date
from typing import Any
import structlog
from integrations.base import BaseFieldMapper

logger = structlog.get_logger(__name__)


class ServiceNowFieldMapper(BaseFieldMapper):
    FIELD_MAPPINGS = {
        "name": "short_description",
        "description": "description",
        "status": "state",  # Int mapped field
        "priority": "priority",  # Int mapped field
        "eta": "due_date",
    }

    FIELD_MAPPINGS_OPERATIONS = {
        "name": {"pull": {"create"}, "push": {"create", "update"}},
        "description": {"pull": {"create"}, "push": {"create", "update"}},
        "status": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "priority": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "eta": {"pull": {"create", "update"}, "push": {"create", "update"}},
    }

    # ServiceNow Standard Incident States (These vary by table!)
    # 1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled
    STATUS_MAP_TO_SNOW = {
        "to_do": 1,
        "in_progress": 2,
        "on_hold": 3,
        "active": 2,  # Mapping 'active' to In Progress
        "deprecated": 7,
    }
    STATUS_MAP_FROM_SNOW = {v: k for k, v in STATUS_MAP_TO_SNOW.items()}

    # ServiceNow Priority: 1=Critical, 2=High, 3=Moderate, 4=Low, 5=Planning
    # AppliedControl Priority: 1=P1, 2=P2...
    PRIORITY_MAP_TO_SNOW = {
        1: 1,  # P1 -> Critical
        2: 2,  # P2 -> High
        3: 3,  # P3 -> Moderate
        4: 4,  # P4 -> Low
    }
    PRIORITY_MAP_FROM_SNOW = {v: k for k, v in PRIORITY_MAP_TO_SNOW.items()}

    def to_remote(self, local_object) -> dict[str, Any]:
        """Convert local object to remote format."""
        # Note: We don't need _strip_fields_prefix because ServiceNow JSON is flat
        return super().to_remote(local_object)

    def to_remote_partial(self, local_object, changed_fields) -> dict[str, Any]:
        return super().to_remote_partial(local_object, changed_fields)

    def to_local(self, remote_data: dict[str, Any]) -> dict[str, Any]:
        # Unwrap 'fields' if it was wrapped in the client,
        # but client.get_remote_object puts the flat dict in 'fields' key already.
        data_to_map = remote_data.get("fields", remote_data)

        allowed_fields = self.get_allowed_fields("pull", "update")
        local_data = {}

        for local_field, remote_field in self._get_mappings().items():
            if local_field in allowed_fields and remote_field in data_to_map:
                val = data_to_map[remote_field]
                local_data[local_field] = self._transform_value_to_local(
                    local_field, val
                )

        return local_data

    def get_allowed_fields(self, direction: str, operation: str) -> set[str]:
        """
        Get allowed fields for a given sync direction and operation.
        Checks the FIELD_MAPPINGS_OPERATIONS dictionary.
        """
        allowed = set()
        for field, ops in self.FIELD_MAPPINGS_OPERATIONS.items():
            if operation in ops.get(direction, set()):
                allowed.add(field)
        return allowed

    def _transform_value_to_remote(self, field: str, value: Any) -> Any:
        if value is None:
            return ""

        if field == "status":
            return self.STATUS_MAP_TO_SNOW.get(value, 1)  # Default to New

        elif field == "priority":
            return self.PRIORITY_MAP_TO_SNOW.get(value, 3)  # Default to Moderate

        elif field in ["eta", "start_date"]:
            if isinstance(value, (datetime, date)):
                return value.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )  # SNOW prefers full datetime string
            return str(value)

        return str(value)

    def _transform_value_to_local(self, field: str, value: Any) -> Any:
        if not value:
            return None

        if field == "status":
            # SNOW API returns values as strings even if they are ints logic-wise ("1")
            try:
                int_val = int(value)
                return self.STATUS_MAP_FROM_SNOW.get(int_val, "to_do")
            except ValueError:
                return "to_do"

        elif field == "priority":
            try:
                int_val = int(value)
                return self.PRIORITY_MAP_FROM_SNOW.get(int_val, 3)
            except ValueError:
                return 3

        elif field == "eta":
            # ServiceNow returns 'YYYY-MM-DD HH:MM:SS'
            try:
                return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S").date()
            except ValueError:
                return None

        return value
