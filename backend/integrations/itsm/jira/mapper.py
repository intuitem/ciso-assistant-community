from datetime import date, datetime
from typing import Any

import structlog
from django.db import models

from integrations.base import BaseFieldMapper

logger = structlog.get_logger(__name__)


class JiraFieldMapper(BaseFieldMapper):
    """Maps fields between AppliedControl and Jira issues.

    Mappings can be configured per-instance via ``settings.field_map`` and
    ``settings.value_map``. When both are empty, the mapper falls back to the
    legacy hardcoded defaults so existing integrations keep working without a
    migration step.
    """

    # Legacy defaults used as a fallback when the configuration carries no
    # dynamic mappings yet. Remote field names are flat (Jira's ``fields.*``
    # nesting is handled at (de)serialization time).
    _DEFAULT_FIELD_MAP: dict[str, str] = {
        "name": "summary",
        "description": "description",
        "status": "status",
        "priority": "priority",
        "eta": "duedate",
    }

    _DEFAULT_VALUE_MAP_TO_REMOTE: dict[str, dict[str, str]] = {
        "status": {
            "to_do": "To Do",
            "in_progress": "In Progress",
            "on_hold": "On Hold",
            "active": "Active",
            "deprecated": "Closed",
        },
        "priority": {
            "1": "Highest",
            "2": "High",
            "3": "Medium",
            "4": "Low",
        },
    }

    # Pull-only aliases for priority values that don't have a 1:1 local
    # equivalent. The CISO model has 4 priorities, Jira has 5, so the legacy
    # mapping collapsed Lowest -> 4 (same as Low) and Highest -> 1 (same as
    # the explicit map below). Without these aliases, issues with priority
    # "Lowest" or "Highest" land as None on pull when the user's value_map
    # only carries the canonical four labels.
    _PRIORITY_PULL_ALIASES: dict[str, str] = {
        "Highest": "1",
        "Lowest": "4",
    }

    # Defines which fields are pushed/pulled and on which operations. Fields
    # outside this map are ignored even if the user configured a mapping for
    # them, so business rules around immutability survive UI configuration.
    FIELD_MAPPINGS_OPERATIONS = {
        "name": {"pull": {"create"}, "push": {"create", "update"}},
        "description": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "status": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "priority": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "eta": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "ref_id": {"pull": {"create", "update"}, "push": {"create", "update"}},
    }

    def __init__(self, configuration):
        super().__init__(configuration)
        self.settings = configuration.settings or {}

        field_map = self.settings.get("field_map") or {}
        value_map = self.settings.get("value_map") or {}

        # Fall back to defaults independently per map. The earlier "use
        # defaults only when both are empty" rule meant that a config with
        # any value_map row (even one) silently dropped the field_map
        # defaults, so e.g. Jira creation lost ``name -> summary`` and failed
        # with "summary required".
        if field_map:
            self.field_map = dict(field_map)
        else:
            self.field_map = dict(self._DEFAULT_FIELD_MAP)

        if value_map:
            self.value_map_to_remote = {
                field: {str(k): v for k, v in mapping.items()}
                for field, mapping in value_map.items()
            }
        else:
            self.value_map_to_remote = {
                field: dict(mapping)
                for field, mapping in self._DEFAULT_VALUE_MAP_TO_REMOTE.items()
            }

        self.value_map_to_local: dict[str, dict[str, Any]] = {}
        for field, mapping in self.value_map_to_remote.items():
            self.value_map_to_local[field] = {
                str(remote_val): local_val for local_val, remote_val in mapping.items()
            }

        # Backfill priority aliases the user's saved value_map can't express.
        priority_local = self.value_map_to_local.setdefault("priority", {})
        for remote_label, local_val in self._PRIORITY_PULL_ALIASES.items():
            priority_local.setdefault(remote_label, local_val)

    def suggest_mapping_for_table(self, table_name: str, client) -> dict[str, Any]:
        """Filter the legacy defaults against what the chosen project + issue
        type actually exposes, so the UI can pre-populate rows the user would
        almost certainly pick themselves.
        """
        columns = client.get_table_columns(table_name)
        column_names = {c.get("name") for c in columns if c.get("name")}

        field_map = {
            local: remote
            for local, remote in self._DEFAULT_FIELD_MAP.items()
            if remote in column_names
        }

        value_map: dict[str, dict[str, str]] = {}
        for local_field, label_map in self._DEFAULT_VALUE_MAP_TO_REMOTE.items():
            remote_field = field_map.get(local_field)
            if not remote_field:
                continue
            choices = client.get_field_choices(table_name, remote_field) or []
            # Build a case-insensitive lookup so we can return Jira's canonical
            # casing (matters for status names like "In Progress" vs "in progress").
            label_lookup = {
                str(c.get("label", "")).lower(): c.get("label")
                for c in choices
                if c.get("label")
            }
            matched = {
                local_val: label_lookup[remote_label.lower()]
                for local_val, remote_label in label_map.items()
                if remote_label.lower() in label_lookup
            }
            if matched:
                value_map[local_field] = matched

        return {"field_map": field_map, "value_map": value_map}

    def _get_mappings(self) -> dict[str, str]:
        return self.field_map

    def get_allowed_fields(self, direction: str, operation: str) -> set[str]:
        allowed = set()
        for field, ops in self.FIELD_MAPPINGS_OPERATIONS.items():
            if operation in ops.get(direction, set()):
                allowed.add(field)
        return allowed

    def to_remote(self, local_object: models.Model) -> dict[str, Any]:
        allowed_fields = self.get_allowed_fields("push", "create")
        remote_data = {}
        for local_field, remote_field in self._get_mappings().items():
            if local_field not in allowed_fields or not remote_field:
                continue
            value = self._get_local_value(local_object, local_field)
            if value is None:
                continue
            transformed = self._transform_value_to_remote(local_field, value)
            if transformed is not None:
                remote_data[remote_field] = transformed
        return remote_data

    def to_remote_partial(
        self, local_object: models.Model, changed_fields: list[str]
    ) -> dict[str, Any]:
        allowed_fields = self.get_allowed_fields("push", "update")
        remote_data = {}
        mappings = self._get_mappings()
        for local_field in changed_fields:
            if local_field not in allowed_fields or local_field not in mappings:
                continue
            remote_field = mappings[local_field]
            if not remote_field:
                continue
            value = self._get_local_value(local_object, local_field)
            if value is None:
                continue
            transformed = self._transform_value_to_remote(local_field, value)
            if transformed is not None:
                remote_data[remote_field] = transformed
        return remote_data

    def to_local(self, remote_data: dict[str, Any]) -> dict[str, Any]:
        # Jira webhook payloads nest values under ``fields``; ServiceNow does
        # too. Unwrap it so configured remote field names stay flat.
        data_to_map = remote_data.get("fields", remote_data)

        allowed_fields = self.get_allowed_fields("pull", "update")
        local_data: dict[str, Any] = {}

        for local_field, remote_field in self._get_mappings().items():
            if local_field not in allowed_fields or not remote_field:
                continue
            if remote_field not in data_to_map:
                continue
            value = data_to_map[remote_field]
            transformed = self._transform_value_to_local(local_field, value)
            if transformed is not None:
                local_data[local_field] = transformed
        return local_data

    def _transform_value_to_remote(self, field: str, value: Any) -> Any:
        if value is None:
            return None

        remote_field = self.field_map.get(field)

        if field == "status":
            # ``--`` is AppliedControl.Status.UNDEFINED, the default for a
            # control with no status set. It has no Jira equivalent, so drop it
            # rather than attempting a transition to a status named "--".
            if str(value) == "--":
                return None
            return self._map_value_to_remote(field, value, default=str(value))

        if field == "priority":
            mapped = self._map_value_to_remote(field, value, default=None)
            if mapped is None:
                return None
            if remote_field == "priority":
                # Jira's system priority field expects an object with ``name``.
                return {"name": str(mapped)}
            return mapped

        if field in ("eta", "start_date"):
            if isinstance(value, datetime):
                return value.date().isoformat()
            if isinstance(value, date):
                return value.isoformat()
            if hasattr(value, "isoformat"):
                return value.isoformat()
            return str(value)

        if field == "description":
            # The client talks to Jira's REST v2 API, which expects a plain
            # string for ``description``. Sending ADF (the v3 doc format) is
            # rejected with HTTP 400 "Operation value must be a string".
            # Custom text fields likewise take a plain string.
            return str(value)

        if field in self.value_map_to_remote:
            return self._map_value_to_remote(field, value, default=str(value))

        return value

    def _transform_value_to_local(self, field: str, value: Any) -> Any:
        if value is None:
            return None

        if field == "status":
            status_name = self._extract_jira_named_value(value)
            if status_name is None:
                logger.warning("Received unexpected value for status", value=value)
                return None
            mapped = self._map_value_to_local(field, status_name)
            if mapped is not None:
                return mapped
            # Case-insensitive fallback for legacy mappings keyed by lowercase
            # Jira status names.
            mapping = self.value_map_to_local.get(field, {})
            for key, local_val in mapping.items():
                if key.lower() == status_name.lower():
                    return local_val
            return None

        if field == "priority":
            priority_name = self._extract_jira_named_value(value)
            if priority_name is None:
                logger.warning("Received unexpected value for priority", value=value)
                return None
            mapped = self._map_value_to_local(field, priority_name)
            if mapped is None:
                return None
            try:
                return int(mapped)
            except (TypeError, ValueError):
                return mapped

        if field in ("eta", "start_date"):
            if isinstance(value, str):
                try:
                    return date.fromisoformat(value[:10])
                except ValueError:
                    try:
                        return datetime.fromisoformat(
                            value.replace("Z", "+00:00")
                        ).date()
                    except ValueError:
                        logger.warning(
                            "Could not parse date string from Jira",
                            field=field,
                            value=value,
                        )
                        return None
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            logger.warning(
                "Received unexpected value for date field", field=field, value=value
            )
            return None

        if field == "description":
            if isinstance(value, dict) and value.get("type") == "doc":
                parts: list[str] = []
                for block in value.get("content", []):
                    if block.get("type") == "paragraph":
                        for item in block.get("content", []):
                            if item.get("type") == "text":
                                parts.append(item.get("text", ""))
                return "\n".join(parts).strip()
            if isinstance(value, str):
                return value.strip()
            logger.warning(
                "Received unexpected format for description", value_type=type(value)
            )
            return str(value) if value else ""

        if field in self.value_map_to_local:
            return self._map_value_to_local(field, value)

        return value

    def _map_value_to_remote(self, field: str, value: Any, default: Any = None) -> Any:
        mapping = self.value_map_to_remote.get(field)
        if not mapping:
            return default
        return mapping.get(str(value), default)

    def _map_value_to_local(self, field: str, value: Any) -> Any:
        mapping = self.value_map_to_local.get(field)
        if not mapping:
            return None
        return mapping.get(str(value))

    @staticmethod
    def _extract_jira_named_value(value: Any) -> str | None:
        """Return the ``name`` from a Jira reference object, or the raw string."""
        if isinstance(value, dict):
            name = value.get("name")
            return name if isinstance(name, str) else None
        if isinstance(value, str):
            return value
        return None
