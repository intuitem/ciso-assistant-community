import hashlib
import hmac
from typing import Any

from django.utils import timezone
from structlog import get_logger

from integrations.base import BaseITSMOrchestrator
from integrations.models import IntegrationSchemaCache
from integrations.registry import IntegrationRegistry

from .client import GLPIClient
from .mapper import GLPIFieldMapper

logger = get_logger(__name__)

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

    def _get_mapper(self, model_key="applied_control"):
        return GLPIFieldMapper(self.configuration, model_key)

    def _get_client(self, model_key="applied_control"):
        return GLPIClient(self.configuration, model_key)

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
        # replay window without rejecting legitimate late deliveries.
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

    def handle_webhook_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        remote_id = self._extract_remote_id(payload)
        if not remote_id:
            logger.warning(
                "Could not extract remote ID from GLPI webhook",
                webhook_event=event_type,
            )
            return False

        if event_type == "update":
            return self.pull_changes(remote_id, self._extract_remote_data(payload))
        if event_type == "delete":
            return self._handle_remote_deletion(remote_id)
        if event_type == "new":
            # Local objects are not created from GLPI items.
            return True

        logger.warning("Unknown GLPI webhook event", webhook_event=event_type)
        return False

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
