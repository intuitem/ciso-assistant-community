import uuid

from django.contrib.contenttypes.models import ContentType
from huey.contrib.djhuey import HUEY, task
from structlog import get_logger

from integrations.itsm.jira.integration import *
from integrations.itsm.servicenow.integration import *
from integrations.models import IntegrationConfiguration

from .registry import IntegrationRegistry

logger = get_logger(__name__)


@task()
def sync_object_to_integrations(
    content_type: ContentType,
    object_id: int,
    config_ids: list[int],
    changed_fields: list[str],
):
    """Push local changes to all configured integrations"""
    from django.apps import apps

    Model = apps.get_model(content_type.app_label, content_type.model)
    obj = Model.objects.get(pk=object_id)

    for config_id in config_ids:
        try:
            config = IntegrationConfiguration.objects.get(pk=config_id)

            # Skip if outgoing sync is disabled
            if not config.settings.get("enable_outgoing_sync", False):
                continue

            orchestrator = IntegrationRegistry.get_orchestrator(config)
            orchestrator.push_changes(obj, changed_fields)
        except Exception as e:
            logger.error(f"Sync failed for config {config_id}: {e}")
            # Don't fail the whole batch if one integration fails


@task()
def warm_servicenow_schema_cache():
    """Pre-fetch ServiceNow schema (tables, columns, choices) into the DB cache
    so the integration settings page loads without live ServiceNow latency.

    Enqueued on Huey consumer startup. Each config is isolated so one failure
    (bad credentials, network) doesn't abort the rest.
    """
    configs = IntegrationConfiguration.objects.filter(
        is_active=True, provider__name="servicenow"
    )
    for config in configs:
        try:
            orchestrator = IntegrationRegistry.get_orchestrator(config)
            orchestrator.refresh_schema()
            logger.info("Warmed ServiceNow schema cache", config_id=str(config.id))
        except Exception as e:
            logger.error(
                f"Failed to warm ServiceNow schema cache for config {config.id}: {e}",
                exc_info=True,
            )


@HUEY.on_startup()
def _enqueue_schema_cache_warmup():
    """Warm the schema cache once the Huey consumer is up. Enqueued (not run
    inline) so worker startup isn't blocked by remote HTTP calls."""
    try:
        warm_servicenow_schema_cache()
    except Exception as e:
        logger.error(f"Failed to enqueue ServiceNow schema cache warmup: {e}")


@task()
def process_webhook_event(config_id: uuid.UUID, event_type: str, payload: dict):
    """Process incoming webhook from remote system"""
    try:
        config = IntegrationConfiguration.objects.get(pk=config_id)

        # Skip if incoming sync is disabled
        if not config.settings.get("enable_incoming_sync", False):
            return

        orchestrator = IntegrationRegistry.get_orchestrator(config)

        # Let the specific orchestrator handle the event
        orchestrator.handle_webhook_event(event_type, payload)

    except IntegrationConfiguration.DoesNotExist:
        logger.error(
            f"process_webhook_event failed: No IntegrationConfiguration found for ID {config_id}"
        )
    except Exception as e:
        logger.error(
            f"process_webhook_event failed for config {config_id}: {e}", exc_info=True
        )
