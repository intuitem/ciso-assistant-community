import hashlib
import hmac
from datetime import datetime
from typing import Any

from django.utils import timezone
from structlog import get_logger

from integrations.base import BaseITSMOrchestrator
from integrations.models import IntegrationSchemaCache, SyncMapping
from integrations.registry import IntegrationRegistry
from integrations.settings_access import get_model_settings

from .client import DEFAULT_ITEM_TYPE, ITEM_TYPES, GLPIClient
from .mapper import GLPIFieldMapper

logger = get_logger(__name__)


_UNREACHABLE = object()


def _modified_at(remote_data: dict[str, Any] | None) -> datetime | None:
    try:
        return datetime.fromisoformat((remote_data or {}).get("updated"))
    except TypeError, ValueError:
        return None


GLPI_CONFIG_SCHEMA = {
    "required": ["credentials", "settings"],
    "credentials": {
        "required": [
            "instance_url",
            "client_id",
            "client_secret",
            "username",
            "password",
        ],
        "properties": {
            "instance_url": {
                "type": "string",
                "description": "e.g., https://glpi.example.com",
            },
            "client_id": {"type": "string", "description": "OAuth client ID"},
            "client_secret": {"type": "string", "description": "OAuth client secret"},
            "username": {"type": "string"},
            "password": {"type": "string"},
        },
    },
    "settings": {
        "properties": {
            "table_name": {
                "type": "string",
                "default": "Ticket",
                "description": "Assistance item type: Ticket, Change or Problem",
            },
            "field_map": {"type": "object"},
            "value_map": {"type": "object"},
            "enable_incoming_sync": {"type": "boolean", "default": True},
            "enable_outgoing_sync": {"type": "boolean", "default": True},
        },
    },
}


class GLPIOrchestrator(BaseITSMOrchestrator):
    client_class = GLPIClient
    mapper_class = GLPIFieldMapper

    # Only applied controls sync with GLPI. A webhook does not name its item
    # type, so a second model under the same configuration could not tell its
    # items from the tickets.
    def _check_model(self, model_key: str) -> None:
        if model_key != self.DEFAULT_MODEL_KEY:
            raise ValueError(f"GLPI does not sync '{model_key}' objects")

    def _get_mapper(self, model_key="applied_control"):
        self._check_model(model_key)
        return GLPIFieldMapper(self.configuration, model_key)

    def _get_client(self, model_key="applied_control"):
        self._check_model(model_key)
        return GLPIClient(self.configuration, model_key)

    @classmethod
    def settings_errors(cls, configuration, new_settings):
        models = new_settings.get("models") or {}
        if not isinstance(models, dict) or not isinstance(
            models.get(cls.DEFAULT_MODEL_KEY) or {}, dict
        ):
            return ["'models' must map a model to its settings."]
        other_models = sorted(set(models) - {cls.DEFAULT_MODEL_KEY})
        if other_models:
            return [
                "GLPI only syncs applied controls. Remove the settings for: "
                + ", ".join(other_models)
            ]
        chosen = get_model_settings(new_settings, cls.DEFAULT_MODEL_KEY).get(
            "table_name"
        )
        if chosen and (not isinstance(chosen, str) or chosen not in ITEM_TYPES):
            return [
                f"Unknown GLPI item type '{chosen}'. Use one of: "
                + ", ".join(ITEM_TYPES)
            ]
        if configuration is None:
            return []

        # Item ids are only unique within an item type: under another type,
        # existing links would address unrelated items with the same id.
        def item_type(settings):
            model_settings = get_model_settings(settings, cls.DEFAULT_MODEL_KEY)
            return model_settings.get("table_name") or DEFAULT_ITEM_TYPE

        old, new = item_type(configuration.settings), item_type(new_settings)
        # Links whose item is still being created count too: its id would be
        # stored under the new type.
        linked = SyncMapping.objects.filter(configuration=configuration)
        if old != new and linked.exists():
            return [
                f"The item type cannot change from {old} to {new} while objects "
                "are linked through this configuration. Unlink them first."
            ]
        return []

    # --- Webhooks -------------------------------------------------------------
    # GLPI webhooks (Setup > Webhooks) post {"event": ..., "item": {...}}, the
    # item being the same representation the API returns.

    def validate_webhook_request(self, request) -> bool:
        signature = request.headers.get("X-GLPI-signature")
        timestamp = request.headers.get("X-GLPI-timestamp")
        if not signature or not timestamp:
            raise ValueError("Missing GLPI signature headers")

        secret = self.configuration.webhook_secret
        if not secret:
            raise ValueError("Webhook secret not configured on server")

        # GLPI signs the body followed by the timestamp. The timestamp is set
        # when the event is queued and reused on retries, so it cannot bound a
        # replay window without rejecting legitimate late deliveries. An event
        # is therefore only a signal: handle_webhook_event reads the item back
        # from GLPI instead of trusting what the delivery carries.
        expected = hmac.new(
            secret.encode("utf-8"),
            request.body + timestamp.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def extract_webhook_event_type(self, payload: dict) -> str:
        return payload.get("event")

    def _extract_remote_id(self, payload: dict[str, Any]) -> str:
        item_id = (payload.get("item") or {}).get("id")
        return str(item_id) if item_id is not None else ""

    def _extract_remote_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        return GLPIClient.normalize_item(payload.get("item") or {})

    def _is_linked(self, remote_id: str) -> bool:
        return SyncMapping.objects.filter(
            configuration=self.configuration, remote_id=remote_id
        ).exists()

    def _read_current(self, remote_id: str):
        """The item as GLPI holds it now: its data, None once it is gone, or
        _UNREACHABLE when GLPI cannot be asked."""
        try:
            return self.client.read_item(remote_id)
        except Exception:
            logger.warning(
                "Could not read the GLPI item back for a webhook",
                remote_id=remote_id,
                exc_info=True,
            )
            return _UNREACHABLE

    def _is_outdated(self, remote_id: str, remote_data: dict[str, Any]) -> bool:
        """True when the event carries an older GLPI modification date than the
        state last synced for this item. Only used when the item cannot be read
        back: applying such an event would bring old values back."""
        incoming = _modified_at(remote_data)
        if incoming is None:
            return False
        synced = _modified_at(
            SyncMapping.objects.filter(
                configuration=self.configuration, remote_id=remote_id
            )
            .values_list("remote_data", flat=True)
            .first()
        )
        try:
            return synced is not None and incoming < synced
        except TypeError:
            # One date carries an offset and the other does not.
            return False

    def handle_webhook_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        remote_id = self._extract_remote_id(payload)
        if not remote_id:
            logger.warning(
                "Could not extract remote ID from GLPI webhook",
                webhook_event=event_type,
            )
            return False

        if event_type == "new":
            # Local objects are not created from GLPI items.
            return True
        if event_type not in ("update", "delete"):
            logger.warning("Unknown GLPI webhook event", webhook_event=event_type)
            return False
        if not self._is_linked(remote_id):
            # Most items in GLPI have nothing to do with CISO Assistant.
            return False

        # GLPI renders the delivery when the change happens and sends it later,
        # possibly after newer changes or more than once. What is applied is
        # the item as GLPI holds it now.
        current = self._read_current(remote_id)

        if event_type == "delete":
            if isinstance(current, dict) and not current["fields"].get("is_deleted"):
                logger.info(
                    "Ignoring GLPI delete webhook: the item still exists",
                    remote_id=remote_id,
                )
                return True
            return self._handle_remote_deletion(remote_id)

        if isinstance(current, dict):
            return self.pull_changes(remote_id, current)

        remote_data = self._extract_remote_data(payload)
        if self._is_outdated(remote_id, remote_data):
            logger.info(
                "Ignoring GLPI webhook older than the synced state",
                remote_id=remote_id,
            )
            return True
        return self.pull_changes(remote_id, remote_data)

    # --- Schema cache ---------------------------------------------------------
    # The schema comes from the instance's OpenAPI document, a multi-megabyte
    # download that describes every item type at once. It is parsed in one go
    # and stored whole; reads never hit GLPI once the cache is populated.

    def _load_schema(self, force: bool = False) -> IntegrationSchemaCache:
        cache, _ = IntegrationSchemaCache.objects.get_or_create(
            configuration=self.configuration
        )
        if force or not cache.tables:
            cache.tables, cache.columns, cache.choices = self.client.fetch_schema()
            cache.fetched_at = timezone.now()
            cache.save(
                update_fields=[
                    "tables",
                    "columns",
                    "choices",
                    "fetched_at",
                    "updated_at",
                ]
            )
            logger.info(
                "Refreshed GLPI schema cache",
                config_id=str(self.configuration.id),
                force=force,
            )
        return cache

    def refresh_schema(self, force: bool = True) -> list[dict]:
        return self._load_schema(force=force).tables

    # Cache-backed lookups, in the client's signature so the mapper can build
    # its suggestions without a live fetch.
    def get_table_columns(self, table_name: str) -> list[dict]:
        return self._load_schema().columns.get(table_name, [])

    def get_field_choices(self, table_name: str, field_name: str) -> list[dict]:
        return self._load_schema().choices.get(f"{table_name}:{field_name}", [])

    def get_interactive_actions(self):
        return [
            "get_tables",
            "get_columns",
            "get_choices",
            "suggest_mapping",
            "refresh_schema",
        ]

    def execute_action(self, action: str, params: dict):
        if action == "refresh_schema":
            return self.refresh_schema()

        if action == "get_tables":
            return self._load_schema().tables

        table = params.get("table_name")
        if not table:
            raise ValueError(f"Parameter 'table_name' is required for {action}")

        if action == "get_columns":
            return self.get_table_columns(table)

        if action == "get_choices":
            field = params.get("field_name")
            if not field:
                raise ValueError("Parameter 'field_name' is required for get_choices")
            return self.get_field_choices(table, field)

        if action == "suggest_mapping":
            model_key = params.get("model_key", self.DEFAULT_MODEL_KEY)
            return self.mapper_for(model_key).suggest_mapping_for_table(table, self)

        raise NotImplementedError(f"Unknown action: {action}")


IntegrationRegistry.register(
    name="glpi",
    provider_type="itsm",
    client_class=GLPIClient,
    mapper_class=GLPIFieldMapper,
    orchestrator_class=GLPIOrchestrator,
    display_name="GLPI",
    description="Sync with GLPI assistance items (tickets, changes, problems)",
    config_schema=GLPI_CONFIG_SCHEMA,
)
