from datetime import datetime, date
from typing import Any
import structlog
from integrations.base import BaseFieldMapper
from core.models import AppliedControl

logger = structlog.get_logger(__name__)


class ServiceNowFieldMapper(BaseFieldMapper):
    FIELD_MAPPINGS_OPERATIONS = {
        "name": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "description": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "status": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "priority": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "eta": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "ref_id": {"pull": {"create", "update"}, "push": {"create", "update"}},
    }

    def __init__(self, configuration):
        super().__init__(configuration)
        self.settings = configuration.settings or {}

        # Load Dynamic Maps
        # Format: { "local_field": "remote_field" }
        self.field_map = self.settings.get("field_map", {})

        # Format: { "local_field": { "local_value": "remote_value" } }
        self.value_map_to_remote = self.settings.get("value_map", {})

        # Build Reverse Map for Incoming Sync (Remote -> Local)
        # Format: { "local_field": { "remote_value_str": "local_value" } }
        self.value_map_to_local = {}
        for field, mapping in self.value_map_to_remote.items():
            self.value_map_to_local[field] = {
                str(remote_val): local_val for local_val, remote_val in mapping.items()
            }

    def _get_mappings(self) -> dict[str, str]:
        """
        Returns the dictionary mapping Local Field Name -> Remote Field Name.
        """
        return self.field_map

    def to_remote(self, local_object) -> dict[str, Any]:
        """Convert local object to remote format."""
        return super().to_remote(local_object)

    def to_remote_partial(self, local_object, changed_fields) -> dict[str, Any]:
        return super().to_remote_partial(local_object, changed_fields)

    def to_local(self, remote_data: dict[str, Any]) -> dict[str, Any]:
        # Unwrap 'fields' if present (ServiceNow Table API often puts data there)
        data_to_map = remote_data.get("fields", remote_data)

        allowed_fields = self.get_allowed_fields("pull", "update")
        local_data = {}

        # Iterate over configured map: Local Key -> Remote Key
        for local_field, remote_field in self._get_mappings().items():
            # Only process fields that are technically allowed AND present in the payload
            if local_field in allowed_fields and remote_field in data_to_map:
                val = data_to_map[remote_field]
                local_data[local_field] = self._transform_value_to_local(
                    local_field, val
                )

        return local_data

    def get_allowed_fields(self, direction: str, operation: str) -> set[str]:
        allowed = set()
        for field, ops in self.FIELD_MAPPINGS_OPERATIONS.items():
            if operation in ops.get(direction, set()):
                allowed.add(field)
        return allowed

    def _transform_value_to_remote(self, field: str, value: Any) -> Any:
        if value is None:
            return ""

        # Handle Value Mapping (Choices)
        if field in self.value_map_to_remote:
            mapping = self.value_map_to_remote[field]
            # Convert to string because JSON keys are strings (e.g. Priority 1 vs "1")
            val_str = str(value)
            if val_str in mapping:
                return mapping[val_str]
            # Fallback: If map exists but value not found, we generally send as-is
            # or you could return a default if strictness is required.

        # Handle Date/Time Formats
        if field in ["eta", "start_date"] and isinstance(value, (datetime, date)):
            return value.strftime("%Y-%m-%d %H:%M:%S")

        return str(value)

    def _transform_value_to_local(self, field: str, value: Any) -> Any:
        if value is None or value == "":
            return None

        # Handle Value Mapping (Choices)
        if field in self.value_map_to_local:
            mapping = self.value_map_to_local[field]
            # ServiceNow values come as strings (even integers like "1")
            val_str = str(value)
            if val_str in mapping:
                return mapping[val_str]
            # Legacy/Safety Fallback for unmapped choice values:
            # if field == "priority":
            #     return 3  # Default P3
            # if field == "status":
            #     return "to_do"

        # Handle Date/Time Parsing
        if field == "eta":
            try:
                return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S").date()
            except ValueError:
                return None

        # Handle Generic Type Conversions
        if field == "priority":
            # If no map was hit above, try to keep it an integer
            try:
                if int(value) not in [p[0] for p in AppliedControl.PRIORITY]:
                    return None
                return int(value)
            except (ValueError, TypeError):
                return None

        return value
