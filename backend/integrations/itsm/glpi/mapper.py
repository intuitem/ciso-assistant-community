import html
import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any

import structlog
from django.db import models

from integrations.base import BaseFieldMapper

logger = structlog.get_logger(__name__)

# GLPI rich-text property the description maps to by default. Its API format
# is HTML, while local descriptions are plain text.
RICH_TEXT_FIELD = "content"

_BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}


class _TextExtractor(HTMLParser):
    """Flatten GLPI rich text to plain text, one line per block element."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    text = "".join(parser.parts)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def text_to_html(value: str) -> str:
    return "".join(f"<p>{html.escape(line)}</p>" for line in value.splitlines())


class GLPIFieldMapper(BaseFieldMapper):
    """Maps fields between local objects and GLPI assistance items.

    Mappings are configured per instance through ``settings.field_map`` and
    ``settings.value_map``. Applied controls fall back to defaults targeting
    the Ticket schema when a map is empty, so a freshly saved configuration
    syncs without further setup.
    """

    _DEFAULT_FIELD_MAP: dict[str, str] = {
        "name": "name",
        "description": RICH_TEXT_FIELD,
        "status": "status",
        "priority": "priority",
        "eta": "resolution_date",
    }

    # Remote values are GLPI ids, stringified because the FieldMapper stores
    # choice values as JSON object keys.
    _DEFAULT_VALUE_MAP_TO_REMOTE: dict[str, dict[str, str]] = {
        "status": {
            "to_do": "1",  # New
            "in_progress": "2",  # Processing (assigned)
            "on_hold": "4",  # Pending
            "active": "5",  # Solved
        },
        "priority": {
            "1": "5",  # Very high
            "2": "4",  # High
            "3": "3",  # Medium
            "4": "2",  # Low
        },
    }

    # Pull-only aliases for remote values a one-to-one value_map cannot express:
    # GLPI has more statuses and priorities than the local model.
    _PULL_ALIASES: dict[str, dict[str, str]] = {
        "status": {
            "3": "in_progress",  # Processing (planned)
            "6": "active",  # Closed
        },
        "priority": {
            "1": "4",  # Very low
            "6": "1",  # Major
        },
    }

    FIELD_MAPPINGS_OPERATIONS = {
        "name": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "description": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "status": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "priority": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "eta": {"pull": {"create", "update"}, "push": {"create", "update"}},
        "ref_id": {"pull": {"create", "update"}, "push": {"create", "update"}},
    }

    def __init__(self, configuration, model_key="applied_control"):
        super().__init__(configuration, model_key)

        field_map = self.model_settings.get("field_map") or {}
        value_map = self.model_settings.get("value_map") or {}

        # The defaults describe AppliedControl <-> Ticket. Other models are
        # purely settings-driven: empty config means nothing is mapped.
        use_defaults = self.model_key == "applied_control"

        if field_map:
            self.field_map = dict(field_map)
        elif use_defaults:
            self.field_map = dict(self._DEFAULT_FIELD_MAP)
        else:
            self.field_map = {}

        if value_map:
            self.value_map_to_remote = {
                field: {str(k): v for k, v in mapping.items()}
                for field, mapping in value_map.items()
            }
        elif use_defaults:
            self.value_map_to_remote = {
                field: dict(mapping)
                for field, mapping in self._DEFAULT_VALUE_MAP_TO_REMOTE.items()
            }
        else:
            self.value_map_to_remote = {}

        self.value_map_to_local: dict[str, dict[str, Any]] = {}
        for field, mapping in self.value_map_to_remote.items():
            self.value_map_to_local[field] = {
                str(remote_val): local_val for local_val, remote_val in mapping.items()
            }

        if use_defaults:
            for field, aliases in self._PULL_ALIASES.items():
                to_local = self.value_map_to_local.setdefault(field, {})
                for remote_val, local_val in aliases.items():
                    to_local.setdefault(remote_val, local_val)

    def suggest_mapping_for_table(self, table_name: str, client) -> dict[str, Any]:
        """Defaults intersected with what the chosen item type exposes."""
        if self.model_key != "applied_control":
            return {"field_map": {}, "value_map": {}}

        columns = client.get_table_columns(table_name)
        column_names = {c.get("name") for c in columns if c.get("name")}

        field_map = {
            local: remote
            for local, remote in self._DEFAULT_FIELD_MAP.items()
            if remote in column_names
        }

        value_map: dict[str, dict[str, str]] = {}
        for local_field, defaults in self._DEFAULT_VALUE_MAP_TO_REMOTE.items():
            remote_field = field_map.get(local_field)
            if not remote_field:
                continue
            choices = client.get_field_choices(table_name, remote_field) or []
            known = {str(c.get("value")) for c in choices}
            matched = {
                local_val: remote_val
                for local_val, remote_val in defaults.items()
                if remote_val in known
            }
            if matched:
                value_map[local_field] = matched

        return {"field_map": field_map, "value_map": value_map}

    def _get_mappings(self) -> dict[str, str]:
        return self.field_map

    def to_remote(self, local_object: models.Model) -> dict[str, Any]:
        return self._to_remote(
            local_object,
            self._get_mappings().keys(),
            self.get_allowed_fields("push", "create"),
        )

    def to_remote_partial(
        self, local_object: models.Model, changed_fields: list[str]
    ) -> dict[str, Any]:
        return self._to_remote(
            local_object, changed_fields, self.get_allowed_fields("push", "update")
        )

    def _to_remote(self, local_object, local_fields, allowed_fields) -> dict[str, Any]:
        remote_data = {}
        mappings = self._get_mappings()
        for local_field in local_fields:
            remote_field = mappings.get(local_field)
            if local_field not in allowed_fields or not remote_field:
                continue
            value = self._get_local_value(local_object, local_field)
            if value is None:
                continue
            transformed = self._transform_value_to_remote(local_field, value)
            if transformed is not None:
                remote_data[remote_field] = transformed
        return remote_data

    def to_local(self, remote_data: dict[str, Any]) -> dict[str, Any]:
        data_to_map = remote_data.get("fields", remote_data)

        allowed_fields = self.get_allowed_fields("pull", "update")
        local_data: dict[str, Any] = {}

        for local_field, remote_field in self._get_mappings().items():
            if local_field not in allowed_fields or not remote_field:
                continue
            if remote_field not in data_to_map:
                continue
            transformed = self._transform_value_to_local(
                local_field, data_to_map[remote_field]
            )
            if transformed is not None:
                local_data[local_field] = transformed
        return local_data

    def _transform_value_to_remote(self, field: str, value: Any) -> Any:
        if value is None:
            return None

        if field in self.value_map_to_remote or field in ("status", "priority"):
            # Unmapped choices are dropped: GLPI rejects values outside its
            # enums, and a local "--" status has no remote counterpart.
            mapped = self.value_map_to_remote.get(field, {}).get(str(value))
            if mapped is None:
                return None
            # GLPI enums are integer ids.
            return int(mapped) if str(mapped).isdigit() else mapped

        if field == "eta":
            if isinstance(value, datetime):
                return value.date().isoformat()
            if isinstance(value, date):
                return value.isoformat()
            return str(value)

        if self.field_map.get(field) == RICH_TEXT_FIELD:
            return text_to_html(str(value))

        return str(value)

    def _transform_value_to_local(self, field: str, value: Any) -> Any:
        if value is None or value == "":
            return None

        if field in self.value_map_to_local or field in ("status", "priority"):
            # Dropdown properties come back as {"id": ..., "name": ...}.
            remote_val = value.get("id") if isinstance(value, dict) else value
            mapped = self.value_map_to_local.get(field, {}).get(str(remote_val))
            if mapped is None:
                return None
            if field == "priority":
                try:
                    return int(mapped)
                except TypeError, ValueError:
                    return None
            return mapped

        if field == "eta":
            # Keep the calendar day GLPI shows: the offset is the instance's
            # own timezone, so converting to UTC could shift the date.
            try:
                return date.fromisoformat(str(value)[:10])
            except ValueError:
                logger.warning("Could not parse date from GLPI", value=value)
                return None

        if self.field_map.get(field) == RICH_TEXT_FIELD:
            return html_to_text(str(value))

        if isinstance(value, (dict, list)):
            logger.warning(
                "Ignoring non-scalar GLPI value", field=field, value_type=type(value)
            )
            return None

        return value
