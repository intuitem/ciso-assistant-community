from typing import Any, Dict
from django.utils import timezone
from structlog import get_logger
from integrations.base import BaseITSMOrchestrator
from integrations.models import IntegrationSchemaCache
from integrations.registry import IntegrationRegistry
from .client import ServiceNowClient
from .mapper import ServiceNowFieldMapper

logger = get_logger(__name__)

SERVICENOW_CONFIG_SCHEMA = {
    "required": ["credentials", "settings"],
    "credentials": {
        "required": ["instance_url", "username", "password"],
        "properties": {
            "instance_url": {
                "type": "string",
                "description": "e.g., https://instance.service-now.com",
            },
            "username": {"type": "string"},
            "password": {"type": "string"},
        },
    },
    "settings": {
        "required": ["table_name"],
        "properties": {
            "table_name": {"type": "string", "default": "incident"},
            "base_query": {"type": "string", "default": "active=true"},
            "enable_incoming_sync": {"type": "boolean", "default": True},
            "enable_outgoing_sync": {"type": "boolean", "default": True},
        },
    },
}


class ServiceNowOrchestrator(BaseITSMOrchestrator):
    client_class = ServiceNowClient
    mapper_class = ServiceNowFieldMapper

    def _get_mapper(self):
        return ServiceNowFieldMapper(self.configuration)

    def _get_client(self):
        return ServiceNowClient(self.configuration)

    def _extract_remote_id(self, payload: Dict[str, Any]) -> str:
        # Assumes ServiceNow Business Rule sends the record as the root json or under 'result'
        # Payload: { "sys_id": "...", "number": "..." }
        return payload.get("sys_id")

    def _extract_remote_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "key": payload.get("sys_id"),
            "fields": payload,  # The payload itself usually contains the fields
            "updated": payload.get("sys_updated_on"),
        }

    def handle_webhook_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        # Define event types in your ServiceNow 'Business Rule' that calls this webhook
        # e.g., 'sn_update', 'sn_delete'
        remote_id = self._extract_remote_id(payload)
        if not remote_id:
            logger.warning(
                f"Could not extract remote ID from payload for event {event_type}"
            )
            return False

        if event_type == "sn_update":
            remote_data = self._extract_remote_data(payload)
            return self.pull_changes(remote_id, remote_data)
        elif event_type == "sn_delete":
            return self._handle_remote_deletion(remote_id)

        return False

    def get_interactive_actions(self):
        return [
            "get_tables",
            "get_columns",
            "get_choices",
            "suggest_mapping",
            "refresh_schema",
        ]

    # --- Schema cache --------------------------------------------------------
    # ServiceNow schema fetches (tables, columns, choices) are slow: the table
    # list returns thousands of rows, and columns/choices recursively walk the
    # parent-table inheritance chain. Reads go through a DB-backed cache that
    # self-heals on a miss (live fetch + store); startup warming and the
    # 'refresh_schema' action keep it fresh.

    def _get_cache(self) -> IntegrationSchemaCache:
        cache, _ = IntegrationSchemaCache.objects.get_or_create(
            configuration=self.configuration
        )
        return cache

    def _cached_tables(self, force: bool = False) -> list[dict]:
        cache = self._get_cache()
        if force or not cache.tables:
            cache.tables = self.client.get_available_tables()
            cache.fetched_at = timezone.now()
            cache.save(update_fields=["tables", "fetched_at", "updated_at"])
        return cache.tables

    def _cached_columns(self, table: str, force: bool = False) -> list[dict]:
        cache = self._get_cache()
        if force or table not in cache.columns:
            cache.columns[table] = self.client.get_table_columns(table)
            cache.fetched_at = timezone.now()
            cache.save(update_fields=["columns", "fetched_at", "updated_at"])
        return cache.columns[table]

    def _cached_choices(
        self, table: str, field: str, force: bool = False
    ) -> list[dict]:
        cache = self._get_cache()
        key = f"{table}:{field}"
        if force or key not in cache.choices:
            cache.choices[key] = self.client.get_field_choices(table, field)
            cache.fetched_at = timezone.now()
            cache.save(update_fields=["choices", "fetched_at", "updated_at"])
        return cache.choices[key]

    def refresh_schema(self) -> list[dict]:
        """Force re-fetch the page-load set (tables + configured table columns +
        mapped-field choices) and overwrite the cache. Returns the fresh tables.
        """
        tables = self._cached_tables(force=True)

        table = self.configuration.settings.get("table_name")
        if table:
            self._cached_columns(table, force=True)

            field_map = self.configuration.settings.get("field_map", {}) or {}
            value_map = self.configuration.settings.get("value_map", {}) or {}
            for local_field in value_map:
                remote_field = field_map.get(local_field)
                if remote_field:
                    self._cached_choices(table, remote_field, force=True)

        logger.info(
            "Refreshed ServiceNow schema cache", config_id=str(self.configuration.id)
        )
        return tables

    def execute_action(self, action: str, params: dict):
        if action == "get_tables":
            return self._cached_tables()

        elif action == "get_columns":
            table = params.get("table_name")
            if not table:
                raise ValueError("Parameter 'table_name' is required for get_columns")
            return self._cached_columns(table)

        elif action == "get_choices":
            table = params.get("table_name")
            field = params.get("field_name")
            if not table or not field:
                raise ValueError(
                    "Parameters 'table_name' and 'field_name' are required"
                )
            return self._cached_choices(table, field)

        elif action == "refresh_schema":
            return self.refresh_schema()

        elif action == "suggest_mapping":
            table = params.get("table_name")
            if not table:
                raise ValueError(
                    "Parameter 'table_name' is required for suggest_mapping"
                )
            # ServiceNow doesn't ship default mappings yet; the base no-op
            # returns {field_map: {}, value_map: {}} so the frontend stops
            # treating the action as unsupported.
            return self.mapper.suggest_mapping_for_table(table, self.client)

        else:
            raise NotImplementedError(f"Unknown action: {action}")

    def validate_webhook_request(self, request) -> bool:
        """
        Validates the request by checking for a matching secret token header.
        ServiceNow doesn't support HMAC signing natively easily, so we use a
        shared secret header approach.
        """
        # Define the header we expect from ServiceNow
        # (The user must configure this in their Outbound REST Message)
        incoming_secret = request.headers.get("X-CISO-Secret")

        if not incoming_secret:
            # Fallback: check query params if they prefer that method
            # incoming_secret = request.GET.get("secret")
            pass

        if not incoming_secret:
            raise ValueError("Missing authentication header (X-CISO-Secret)")

        configured_secret = self.configuration.webhook_secret
        if not configured_secret:
            raise ValueError("Webhook secret not configured on server")

        # Constant time comparison to prevent timing attacks
        import hmac

        # Compare strings safely
        if not hmac.compare_digest(incoming_secret, configured_secret):
            raise ValueError("Invalid secret token")

        return True

    def extract_webhook_event_type(self, payload: dict) -> str:
        # Based on the Business Rule script we wrote earlier,
        # we inject an "event" field into the JSON body.
        return payload.get("event")


IntegrationRegistry.register(
    name="servicenow",
    provider_type="itsm",
    client_class=ServiceNowClient,
    mapper_class=ServiceNowFieldMapper,
    orchestrator_class=ServiceNowOrchestrator,
    display_name="ServiceNow",
    description="Sync with ServiceNow Tables (Incident, etc)",
    config_schema=SERVICENOW_CONFIG_SCHEMA,
)
