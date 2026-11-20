import hashlib
import hmac
from datetime import datetime
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from structlog import get_logger

from integrations import syncable
from integrations.base import BaseITSMOrchestrator
from integrations.models import IntegrationSchemaCache, SyncMapping
from integrations.registry import IntegrationRegistry
from integrations.settings_access import get_model_settings

from .client import (
    MODEL_ITEM_TYPES,
    GLPIClient,
    item_type_for,
    qualify,
    split_remote_id,
)
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
            "models": {
                "type": "object",
                "description": "Per-model mapping, e.g. models.asset.table_name "
                "for the asset item type (Computer, Software, ...)",
            },
            "enable_incoming_sync": {"type": "boolean", "default": True},
            "enable_outgoing_sync": {"type": "boolean", "default": True},
        },
    },
}


class GLPIOrchestrator(BaseITSMOrchestrator):
    client_class = GLPIClient
    mapper_class = GLPIFieldMapper

    def _check_model(self, model_key: str) -> None:
        if model_key not in MODEL_ITEM_TYPES:
            raise ValueError(f"GLPI does not sync '{model_key}' objects")

    def _get_mapper(self, model_key="applied_control"):
        self._check_model(model_key)
        return GLPIFieldMapper(self.configuration, model_key)

    def _get_client(self, model_key="applied_control"):
        self._check_model(model_key)
        return GLPIClient(self.configuration, model_key)

    @classmethod
    def settings_errors(cls, configuration, new_settings):
        # Types are checked before any default applies: a wrong value must not
        # quietly become the Ticket default. Only a missing or null key is
        # "not set".
        def given(settings: dict, key: str, default):
            value = settings.get(key)
            return default if value is None else value

        models = given(new_settings, "models", {})
        if not isinstance(models, dict) or not all(
            isinstance(given(models, model_key, {}), dict) for model_key in models
        ):
            return ["'models' must map a model to its settings."]
        other_models = sorted(set(models) - set(MODEL_ITEM_TYPES))
        if other_models:
            return [
                "GLPI syncs applied controls and assets. Remove the settings for: "
                + ", ".join(other_models)
            ]
        for model_key, item_types in MODEL_ITEM_TYPES.items():
            model_settings = get_model_settings(new_settings, model_key)
            chosen = given(model_settings, "table_name", "")
            if chosen != "" and chosen not in tuple(item_types):
                return [
                    f"Unknown GLPI item type '{chosen}' for {model_key}. Use one "
                    "of: " + ", ".join(item_types)
                ]
            field_map = given(model_settings, "field_map", {})
            if not isinstance(field_map, dict) or not all(
                remote is None or isinstance(remote, str)
                for remote in field_map.values()
            ):
                return ["'field_map' must map each field to a GLPI property name."]
            value_map = given(model_settings, "value_map", {})
            if not isinstance(value_map, dict) or not all(
                isinstance(choices, dict) for choices in value_map.values()
            ):
                return ["'value_map' must map each field to its value pairs."]
        if configuration is None:
            return []

        # A model's mapping is written for one item type, and its links name
        # that type: under another one they would stop syncing.
        for model_key in MODEL_ITEM_TYPES:
            new = item_type_for(new_settings, model_key)
            if not new:
                # Sync turned off for this model: its links keep their type.
                continue
            spec = syncable.get_spec(model_key)
            # Links whose item is still being created count too.
            linked = list(
                SyncMapping.objects.filter(
                    configuration=configuration,
                    content_type__app_label=spec.app_label,
                    content_type__model=spec.model_name,
                ).values_list("remote_id", flat=True)
            )
            # The type the links name comes first: the setting may have been
            # emptied in between, and must not come back as another type.
            types = sorted({split_remote_id(r)[0] for r in linked} - {None, new})
            old = item_type_for(configuration.settings, model_key)
            if linked and old and old != new:
                types.append(old)
            if types:
                return [
                    f"The item type cannot change from {types[0]} to {new} while "
                    "objects are linked through this configuration. Unlink them "
                    "first."
                ]
        return []

    # --- Links ----------------------------------------------------------------

    def push_changes(self, local_object, changed_fields: list[str]) -> bool:
        content_type = ContentType.objects.get_for_model(local_object)
        model_key = syncable.model_key_for_content_type(content_type)
        if model_key not in MODEL_ITEM_TYPES:
            return super().push_changes(local_object, changed_fields)
        if not self.mapper_for(model_key).field_map:
            # An item type chosen with no field mapped yet: nothing to send,
            # and a creation would leave an empty item in GLPI.
            logger.info(
                "Skipping push: no field is mapped for this model",
                model=model_key,
                config_id=str(self.configuration.id),
            )
            return False

        mapping = SyncMapping.objects.filter(
            configuration=self.configuration,
            content_type=content_type,
            local_object_id=local_object.pk,
        ).first()
        agreed = None
        if mapping:
            self._qualify(mapping, model_key)
            agreed = self._agreed_state(mapping.remote_id, mapping.remote_data)

        pushed = super().push_changes(local_object, changed_fields)
        if pushed and agreed:
            self._keep_unpulled_state(mapping, model_key, agreed, changed_fields)
        return pushed

    def _qualify(self, mapping, model_key: str) -> None:
        """A link made through the API can carry the bare GLPI id. It is
        stored with the model's item type, like the ids this provider issues,
        so that it cannot be taken for an item of another type."""
        item_type = item_type_for(self.configuration.settings, model_key)
        if item_type and mapping.remote_id.strip().isdigit():
            mapping.remote_id = qualify(item_type, mapping.remote_id.strip())
            mapping.save(update_fields=["remote_id"])

    @staticmethod
    def _agreed_state(remote_id: str, remote_data: dict | None) -> dict | None:
        """The state of the linked item that both sides last agreed on: what
        was pulled from GLPI or pushed to it. None when nothing is stored for
        this item, as right after a link is pointed at another one."""
        if not remote_data or not remote_id:
            return None
        if str(remote_data.get("key")) != split_remote_id(remote_id)[1]:
            return None
        return remote_data

    def _keep_unpulled_state(self, mapping, model_key, agreed, changed_fields) -> None:
        """After a push, the agreed state only moves on the fields that were
        pushed. The read that follows a push can already hold a change made in
        GLPI meanwhile: storing it as agreed would make the delivery about it
        look like nothing new, and it would never reach the local object."""
        mapping.refresh_from_db()
        fresh = mapping.remote_data or {}
        if self._agreed_state(mapping.remote_id, fresh) is None:
            return
        field_map = self.mapper_for(model_key).field_map
        fields = dict(agreed.get("fields") or {})
        for remote_field in {field_map.get(field) for field in changed_fields}:
            if remote_field in (fresh.get("fields") or {}):
                fields[remote_field] = fresh["fields"][remote_field]
        mapping.remote_data = {**fresh, "fields": fields}
        mapping.save(update_fields=["remote_data"])

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

    def _linked(self, item_id: str) -> list[tuple[str, str]]:
        """``(model, remote id)`` of each link a delivery for this item id may
        be about. A delivery does not name its item type, so the id is looked
        up under the type of every model this configuration syncs."""
        item_types = {
            model_key: item_type_for(self.configuration.settings, model_key)
            for model_key in MODEL_ITEM_TYPES
        }
        candidates = [qualify(t, item_id) for t in item_types.values() if t]
        linked = []
        for mapping in SyncMapping.objects.filter(
            configuration=self.configuration, remote_id__in=[*candidates, item_id]
        ).select_related("content_type"):
            model_key = syncable.model_key_for_content_type(mapping.content_type)
            if not item_types.get(model_key):
                continue
            # A bare id: linked through the API and not pushed since, which
            # is the normal case when outgoing sync is off.
            self._qualify(mapping, model_key)
            # A link naming another model's item type is not this model's.
            if mapping.remote_id == qualify(item_types[model_key], item_id):
                linked.append((model_key, mapping.remote_id))
        return linked

    def _read_current(self, model_key: str, remote_id: str):
        """The item as GLPI holds it now: its data, None once it is gone, or
        _UNREACHABLE when GLPI cannot be asked."""
        try:
            return self.client_for(model_key).read_item(remote_id)
        except Exception:
            logger.warning(
                "GLPI webhook not applied: the item could not be read back",
                remote_id=remote_id,
                exc_info=True,
            )
            return _UNREACHABLE

    def _synced_state(self, remote_id: str) -> dict[str, Any] | None:
        """The linked item as it was when last synced."""
        stored = (
            SyncMapping.objects.filter(
                configuration=self.configuration, remote_id=remote_id
            )
            .values_list("remote_data", flat=True)
            .first()
        )
        return self._agreed_state(remote_id, stored)

    @staticmethod
    def _is_outdated(synced: dict | None, remote_data: dict[str, Any]) -> bool:
        """True when this state of the item is older than the one already
        synced: two workers can read the item back around the same time and
        finish in the other order."""
        incoming, known = _modified_at(remote_data), _modified_at(synced)
        try:
            return incoming is not None and known is not None and incoming < known
        except TypeError:
            # One date carries an offset and the other does not.
            return False

    def handle_webhook_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        item_id = self._extract_remote_id(payload)
        if not item_id:
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

        # Most items in GLPI have nothing to do with CISO Assistant: no link,
        # nothing to do. A linked item of another type that happens to share
        # the id is read too: what gets applied is that item's own state, as
        # after any delivery about it.
        linked = self._linked(item_id)
        results = [
            self._sync_linked_item(model_key, remote_id, event_type)
            for model_key, remote_id in linked
        ]
        return bool(results) and all(results)

    def _sync_linked_item(self, model_key: str, remote_id: str, event_type: str):
        # GLPI renders the delivery when the change happens and sends it later,
        # possibly after newer changes or more than once. So the delivery only
        # says that something happened: what is acted on is the item as GLPI
        # holds it now, and nothing is done when GLPI cannot be asked.
        current = self._read_current(model_key, remote_id)
        if current is _UNREACHABLE:
            return False

        if current is None or current["fields"].get("is_deleted"):
            # Purged, or in the trash.
            return self._handle_remote_deletion(remote_id)
        if event_type == "delete":
            logger.info(
                "Ignoring GLPI delete webhook: the item still exists",
                remote_id=remote_id,
            )
            return True
        if self._is_outdated(self._synced_state(remote_id), current):
            logger.info(
                "Ignoring a GLPI state older than the synced one",
                remote_id=remote_id,
            )
            return True
        return self.pull_changes(remote_id, current)

    def pull_changes(self, remote_id: str, remote_data: dict[str, Any]) -> bool:
        """Apply what changed in GLPI since the state both sides agreed on.

        The other fields are left alone: a local edit waiting to be pushed is
        not undone by a delivery about something else, whether that delivery
        comes once or several times, and a link made by hand does not copy
        the GLPI item over the local object."""
        strategy = self.configuration.settings.get("conflict_resolution", "remote_wins")
        if strategy != "remote_wins":
            return super().pull_changes(remote_id, remote_data)

        try:
            mapping = SyncMapping.objects.get(
                configuration=self.configuration, remote_id=remote_id
            )
        except SyncMapping.DoesNotExist:
            logger.warning("No mapping found for GLPI item", remote_id=remote_id)
            return False
        except SyncMapping.MultipleObjectsReturned:
            logger.error(
                "Several objects are linked to one GLPI item; skipping pull",
                remote_id=remote_id,
                config_id=str(self.configuration.id),
            )
            return False

        model_key = (
            syncable.model_key_for_content_type(mapping.content_type)
            or self.DEFAULT_MODEL_KEY
        )
        try:
            changed = self._merge_remote_changes(mapping, remote_data, model_key)
        except Exception as error:
            logger.error(
                "Failed to pull changes from GLPI", remote_id=remote_id, exc_info=True
            )
            mapping.sync_status = SyncMapping.SyncStatus.FAILED
            mapping.error_message = str(error)
            mapping.save()
            self._log_sync_event(
                mapping,
                SyncMapping.SyncDirection.PULL,
                [],
                success=False,
                error=str(error),
            )
            return False

        self._log_sync_event(
            mapping, SyncMapping.SyncDirection.PULL, sorted(changed), success=True
        )
        return True

    def _merge_remote_changes(self, mapping, remote_data, model_key) -> dict[str, Any]:
        """Apply the fields whose GLPI value differs from the agreed state,
        which then becomes what GLPI holds. With no agreed state, everything
        GLPI holds applies. Returns the applied fields."""
        mapper = self.mapper_for(model_key)
        incoming = mapper.to_local(remote_data)
        known = mapper.to_local(
            self._agreed_state(mapping.remote_id, mapping.remote_data) or {}
        )
        changed = {
            field: value
            for field, value in incoming.items()
            if field not in known or known[field] != value
        }
        if changed:
            self._update_local_object(self._get_local_object(mapping), changed)

        mapping.sync_status = SyncMapping.SyncStatus.SYNCED
        mapping.last_sync_direction = SyncMapping.SyncDirection.PULL
        mapping.remote_data = remote_data
        mapping.version += 1
        mapping.error_message = ""
        mapping.save()
        logger.info(
            "Pulled changes from GLPI",
            remote_id=mapping.remote_id,
            fields=sorted(changed),
        )
        return changed

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

    def _tables_for(self, model_key: str) -> list[dict]:
        """Item types a model can sync with, among those the instance has."""
        item_types = MODEL_ITEM_TYPES[model_key]

        def offered(cache):
            return [t for t in cache.tables if t.get("name") in item_types]

        # A cache filled before this model was synced lists none of its types.
        return offered(self._load_schema()) or offered(self._load_schema(force=True))

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

        model_key = params.get("model_key", self.DEFAULT_MODEL_KEY)
        if not isinstance(model_key, str) or model_key not in MODEL_ITEM_TYPES:
            raise ValueError(f"GLPI does not sync '{model_key}' objects")

        if action == "get_tables":
            return self._tables_for(model_key)

        table = params.get("table_name")
        if not table or not isinstance(table, str):
            raise ValueError(f"Parameter 'table_name' is required for {action}")

        if action == "get_columns":
            return self.get_table_columns(table)

        if action == "get_choices":
            field = params.get("field_name")
            if not field or not isinstance(field, str):
                raise ValueError("Parameter 'field_name' is required for get_choices")
            return self.get_field_choices(table, field)

        if action == "suggest_mapping":
            return self.mapper_for(model_key).suggest_mapping_for_table(table, self)

        raise NotImplementedError(f"Unknown action: {action}")


IntegrationRegistry.register(
    name="glpi",
    provider_type="itsm",
    client_class=GLPIClient,
    mapper_class=GLPIFieldMapper,
    orchestrator_class=GLPIOrchestrator,
    display_name="GLPI",
    description="Sync with GLPI tickets, changes, problems and assets",
    config_schema=GLPI_CONFIG_SCHEMA,
)
