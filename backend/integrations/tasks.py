import uuid

from django.contrib.contenttypes.models import ContentType
from huey.contrib.djhuey import task
from structlog import get_logger

from integrations.itsm.jira.integration import *
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
    """
    Push a local model instance's changed fields to multiple integration configurations.
    
    Parameters:
    	content_type (ContentType): Django ContentType identifying the model of the object to sync.
    	object_id (int): Primary key of the model instance to fetch and sync.
    	config_ids (list[int]): Iterable of IntegrationConfiguration primary keys to which changes should be pushed.
    	changed_fields (list[str]): Names of the fields on the instance that have changed; passed to each orchestrator.
    """
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
def process_webhook_event(config_id: uuid.UUID, event_type: str, payload: dict):
    """
    Handle a webhook event for the specified integration configuration.
    
    Parameters:
        config_id (uuid.UUID): Primary key of the IntegrationConfiguration to route the event to.
        event_type (str): The remote system's event type identifier.
        payload (dict): Parsed webhook payload provided by the remote system.
    
    Notes:
        If the configuration's `enable_incoming_sync` setting is false, the event is ignored.
        Errors (including missing configuration) are logged; exceptions are not raised to callers.
    """
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