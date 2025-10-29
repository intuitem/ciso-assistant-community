import structlog
from abc import ABC, abstractmethod
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db import models

from core.base_models import AbstractBaseModel
from integrations.models import IntegrationConfiguration, SyncMapping

logger = structlog.get_logger(__name__)


class BaseIntegrationClient(ABC):
    """Base class for all integration clients"""

    def __init__(self, configuration: IntegrationConfiguration):
        """
        Initialize the client with an IntegrationConfiguration and expose its credentials and settings for use by subclasses.
        
        Parameters:
            configuration (IntegrationConfiguration): Integration configuration containing credentials and settings for the integration.
        """
        self.configuration = configuration
        self.credentials = configuration.credentials
        self.settings = configuration.settings

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Verify that the configured integration credentials allow a successful connection to the remote system.
        
        Returns:
            bool: True if the credentials are valid and a connection can be established, False otherwise.
        """
        pass

    @abstractmethod
    def create_remote_object(self, local_object) -> str:
        """
        Create a corresponding object in the remote integration system.
        
        Parameters:
            local_object: The local model instance to create remotely.
        
        Returns:
            remote_id (str): The identifier of the created remote object.
        """
        pass

    @abstractmethod
    def update_remote_object(self, remote_id: str, changes: dict[str, Any]) -> bool:
        """
        Update the corresponding object in the remote integration.
        
        Parameters:
            remote_id (str): Identifier of the remote object to update.
            changes (dict[str, Any]): Mapping of remote-field names to new values to apply.
        
        Returns:
            bool: `true` if the remote update succeeded, `false` otherwise.
        """
        pass

    @abstractmethod
    def get_remote_object(self, remote_id: str) -> dict[str, Any]:
        """
        Retrieve the remote object's data for the given remote identifier.
        
        Returns:
            dict[str, Any]: A dictionary containing the remote object's data.
        """
        pass

    @abstractmethod
    def list_remote_objects(
        self, query_params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve a list of remote objects matching optional query parameters.
        
        Parameters:
            query_params (dict[str, Any] | None): Optional mapping of query, filter, or pagination parameters whose keys and semantics depend on the remote system.
        
        Returns:
            list[dict[str, Any]]: A list of remote objects represented as JSON-like dictionaries.
        """
        pass

    @abstractmethod
    def register_webhook(self, callback_url: str) -> dict[str, Any]:
        """
        Register a webhook endpoint with the remote integration service.
        
        Parameters:
        	callback_url (str): Absolute URL the remote system should call for webhook events.
        
        Returns:
        	webhook_info (dict[str, Any]): Data returned by the remote system describing the registered webhook (e.g. id, target URL, secret, metadata).
        """
        pass

    @abstractmethod
    def unregister_webhook(self, webhook_id: str) -> bool:
        """
        Remove a previously registered webhook from the remote integration.
        
        Parameters:
            webhook_id (str): Identifier of the webhook in the remote system to unregister.
        
        Returns:
            bool: `True` if the webhook was successfully unregistered, `False` otherwise.
        """
        pass


class BaseFieldMapper(ABC):
    """Maps fields between local and remote systems"""

    # Define field mappings as class attributes
    # Format: {'local_field': 'remote_field'}
    FIELD_MAPPINGS: dict[str, str] = {}

    def __init__(self, configuration: IntegrationConfiguration):
        """
        Initialize the mapper with the given integration configuration and load per-instance field mappings.
        
        Parameters:
        	configuration (IntegrationConfiguration): Integration configuration whose settings may include a "field_mappings" entry; that mapping (if present) is stored on the instance as `custom_mappings`.
        """
        self.configuration = configuration
        # Allow per-instance custom mappings
        self.custom_mappings = configuration.settings.get("field_mappings", {})

    def to_remote(self, local_object: models.Model) -> dict[str, Any]:
        """
        Builds a mapping of remote field names to transformed values from a local model instance.
        
        Skips fields whose local value or transformed value is None and only includes fields defined by the mapper's mappings.
        
        Parameters:
            local_object (models.Model): The local Django model instance to convert.
        
        Returns:
            remote_data (dict[str, Any]): Dictionary where keys are remote field names and values are the mapped/transformed values.
        """
        remote_data = {}
        for local_field, remote_field in self._get_mappings().items():
            value = self._get_local_value(local_object, local_field)
            if value is not None:
                transformed = self._transform_value_to_remote(local_field, value)
                if transformed is not None:
                    remote_data[remote_field] = transformed
        return remote_data

    def to_remote_partial(
        self, local_object: models.Model, changed_fields: list[str]
    ) -> dict[str, Any]:
        """
        Builds a dictionary of remote-formatted fields for a subset of local fields.
        
        Only fields present in the mapper's mappings and with non-None transformed values are included.
        
        Parameters:
            local_object (models.Model): The local model instance to read values from.
            changed_fields (list[str]): Local field names to convert; only mapped fields are considered.
        
        Returns:
            dict[str, Any]: Mapping of remote field names to their transformed values.
        """
        remote_data = {}
        mappings = self._get_mappings()

        for local_field in changed_fields:
            if local_field in mappings:
                remote_field = mappings[local_field]
                value = self._get_local_value(local_object, local_field)
                if value is not None:
                    transformed = self._transform_value_to_remote(local_field, value)
                    if transformed is not None:
                        remote_data[remote_field] = transformed

        return remote_data

    def to_local(self, remote_data: dict[str, Any]) -> dict[str, Any]:
        """
        Map a remote object's data into the local model's field representation.
        
        Parameters:
            remote_data (dict[str, Any]): Raw data received from the remote system.
        
        Returns:
            dict[str, Any]: A dictionary of local field names to converted values suitable for assigning to the local model; fields with no value after conversion are omitted.
        """
        local_data = {}
        reverse_mappings = {v: k for k, v in self._get_mappings().items()}

        for remote_field, local_field in reverse_mappings.items():
            # Use helper to get potentially nested value
            value = self._get_remote_value(remote_data, remote_field)
            if value is not None:
                transformed = self._transform_value_to_local(local_field, value)
                if transformed is not None:
                    local_data[local_field] = transformed

        return local_data

    def _get_mappings(self) -> dict[str, str]:
        """
        Merge class-level and instance-level field mappings into a single mapping.
        
        Returns:
            A dictionary mapping local field names to remote field paths where entries from the instance's
            custom mappings override the class-level `FIELD_MAPPINGS`.
        """
        return {**self.FIELD_MAPPINGS, **self.custom_mappings}

    def _get_local_value(self, local_object: models.Model, field_name: str) -> Any:
        """
        Retrieve a value from a local Django model, supporting nested attributes using dot notation.
        
        Parameters:
            local_object (models.Model): The Django model instance to read from.
            field_name (str): The attribute name or dot-separated path (e.g., "owner.name").
        
        Returns:
            Any: The resolved attribute value if present, otherwise `None`.
        """
        if "." in field_name:
            # Handle nested attributes like 'owner.name'
            parts = field_name.split(".")
            value = local_object
            for part in parts:
                value = getattr(value, part, None)
                if value is None:
                    return None
            return value
        return getattr(local_object, field_name, None)

    def _get_remote_value(self, remote_data: dict[str, Any], field_name: str) -> Any:
        """
        Retrieve a value from remote_data using a dot-separated path for nested keys.
        
        Parameters:
            remote_data (dict[str, Any]): The remote object data to read from.
            field_name (str): The key or dot-separated path (e.g., "a.b.c") identifying the value to retrieve.
        
        Returns:
            Any: The value found at the given path, or `None` if any key along the path is missing or an intermediate value is not a dict.
        """
        if "." in field_name:
            parts = field_name.split(".")
            value = remote_data
            for part in parts:
                if not isinstance(value, dict):
                    return None
                value = value.get(part)
                if value is None:
                    return None
            return value
        return remote_data.get(field_name)

    @abstractmethod
    def _transform_value_to_remote(self, field: str, value: Any) -> Any:
        """
        Transform a local field value into the format expected by the remote system.
        
        Parameters:
            field (str): Local field name being transformed.
            value (Any): Value from the local object.
        
        Returns:
            Any: The value converted for the remote system, or `None` to omit this field from remote payloads.
        """
        pass

    @abstractmethod
    def _transform_value_to_local(self, field: str, value: Any) -> Any:
        """
        Convert a value from the remote representation to the local model's format for a specific field.
        
        Parameters:
            field (str): Local field name that determines which transformation to apply.
            value (Any): Value received from the remote system.
        
        Returns:
            Any: Transformed value appropriate for assignment to the local field, or `None` to indicate the field should be skipped.
        """
        pass


class BaseSyncOrchestrator:
    """Orchestrates sync operations between local and remote systems"""

    def __init__(self, configuration: IntegrationConfiguration):
        """
        Initialize the orchestrator with an integration configuration and prepare its client and mapper.
        
        Parameters:
            configuration (IntegrationConfiguration): Integration-specific settings and credentials used to configure the orchestrator, the integration client, and the field mapper.
        """
        self.configuration = configuration
        self.client = self._get_client()
        self.mapper = self._get_mapper()

    @abstractmethod
    def _get_client(self) -> BaseIntegrationClient:
        """
        Provide the integration client instance used by this orchestrator.
        
        Subclasses must implement this to return a configured BaseIntegrationClient tied to the orchestrator's IntegrationConfiguration.
        
        Returns:
            BaseIntegrationClient: An instance of the client configured for this integration.
        """
        pass

    @abstractmethod
    def _get_mapper(self) -> BaseFieldMapper:
        """
        Provide the field mapper used to translate between local model fields and the remote system's representation for this integration.
        
        Returns:
            BaseFieldMapper: A configured mapper instance for this integration.
        """
        pass

    def push_changes(
        self, local_object: models.Model, changed_fields: list[str]
    ) -> bool:
        """
        Pushes changes from a local Django model instance to the remote integration and updates the associated SyncMapping.
        
        Parameters:
            local_object (models.Model): The Django model instance whose changes should be synchronized.
            changed_fields (list[str]): Names of the fields that changed on the local object; used to build a partial update payload.
        
        Returns:
            bool: `true` if the push and mapping update succeeded, `false` otherwise.
        """
        from .models import SyncMapping  # Import here to avoid circular imports

        mapping = self._get_or_create_mapping(local_object)

        try:
            if mapping.remote_id:
                # Update existing remote object
                changes = self.mapper.to_remote_partial(local_object, changed_fields)
                if changes:  # Only update if there are actual changes to sync
                    self.client.update_remote_object(mapping.remote_id, changes)
                    logger.info(
                        f"Updated remote object {mapping.remote_id} with changes: {list(changes.keys())}"
                    )
            else:
                # Create new remote object
                remote_id = self.client.create_remote_object(local_object)
                mapping.remote_id = remote_id
                logger.info("Created remote object", remote_id=remote_id)

            # Update mapping status
            mapping.sync_status = SyncMapping.SyncStatus.SYNCED
            mapping.last_sync_direction = SyncMapping.SyncDirection.PUSH
            mapping.version += 1
            mapping.remote_data = self.client.get_remote_object(mapping.remote_id)
            mapping.error_message = ""
            mapping.save()

            self._log_sync_event(
                mapping, SyncMapping.SyncDirection.PUSH, changed_fields, success=True
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to push changes for {local_object}: {e}", exc_info=True
            )
            mapping.sync_status = SyncMapping.SyncStatus.FAILED
            mapping.error_message = str(e)
            mapping.save()

            self._log_sync_event(
                mapping,
                SyncMapping.SyncDirection.PUSH,
                changed_fields,
                success=False,
                error=str(e),
            )
            return False

    def pull_changes(self, remote_id: str, remote_data: dict[str, Any]) -> bool:
        """
        Apply remote object data to the corresponding local model and update the sync mapping.
        
        If a mapping for `remote_id` cannot be found the function returns `false`. If a conflict between local and remote data is detected the configured conflict resolution is applied and its outcome determines the return value. On success the local object is updated, the mapping's sync metadata is refreshed, and a sync event is logged.
        
        Parameters:
            remote_id (str): Remote object identifier.
            remote_data (dict[str, Any]): Current remote object data to be mapped into the local model.
        
        Returns:
            `true` if the pull and mapping update succeeded, `false` otherwise.
        """
        from .models import SyncMapping  # Import here to avoid circular imports

        try:
            mapping = SyncMapping.objects.get(
                configuration=self.configuration, remote_id=remote_id
            )
        except SyncMapping.DoesNotExist:
            logger.warning(f"No mapping found for remote_id {remote_id}")
            return False

        try:
            # Check for conflicts
            if self._has_conflict(mapping, remote_data):
                logger.warning("Conflict detected for mapping", mapping_id=mapping.id)
                mapping.sync_status = "conflict"
                mapping.save()
                # Handle conflict based on resolution strategy
                return self._resolve_conflict(mapping, remote_data)

            # Convert remote data to local format
            local_data = self.mapper.to_local(remote_data)
            local_object = self._get_local_object(mapping)

            # Apply changes to local object
            self._update_local_object(local_object, local_data)

            # Update mapping status
            mapping.sync_status = SyncMapping.SyncStatus.SYNCED
            mapping.last_sync_direction = SyncMapping.SyncDirection.PULL
            mapping.remote_data = remote_data
            mapping.version += 1
            mapping.error_message = ""
            mapping.save()

            self._log_sync_event(
                mapping,
                SyncMapping.SyncDirection.PULL,
                list(local_data.keys()),
                success=True,
            )
            logger.info(f"Pulled changes from remote {remote_id} to local object")
            return True

        except Exception as e:
            logger.error(f"Failed to pull changes from {remote_id}: {e}", exc_info=True)
            mapping.sync_status = SyncMapping.SyncStatus.FAILED
            mapping.error_message = str(e)
            mapping.save()

            self._log_sync_event(
                mapping, SyncMapping.SyncDirection.PULL, [], success=False, error=str(e)
            )
            return False

    def handle_webhook_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        """
        Route a webhook event to the appropriate sync handler based on the event type.
        
        Extracts the remote object identifier from the payload and dispatches the event to pull, deletion, or an ignored no-op path; returns whether handling succeeded.
        
        Parameters:
            event_type (str): Webhook event kind (e.g., "created", "updated", "deleted").
            payload (dict[str, Any]): Raw webhook payload.
        
        Returns:
            bool: `True` if the event was handled successfully (including intentionally ignored event types), `False` otherwise.
        """
        try:
            remote_id = self._extract_remote_id(payload)
            if not remote_id:
                logger.warning(
                    f"Could not extract remote ID from payload for event {event_type}"
                )
                return False

            if event_type in ["created", "updated"]:
                remote_data = self._extract_remote_data(payload)
                if not remote_data:
                    logger.warning(
                        f"Could not extract remote data from payload for event {event_type}"
                    )
                    return False
                return self.pull_changes(remote_id, remote_data)
            elif event_type == "deleted":
                return self._handle_remote_deletion(remote_id)
            else:
                logger.info(f"Ignoring unhandled event type: {event_type}")
                return True  # Not a failure, just not handled

        except Exception as e:
            logger.error(f"Failed to handle webhook event: {e}", exc_info=True)
            return False

    @abstractmethod
    def _extract_remote_id(self, payload: dict[str, Any]) -> str:
        """
        Extract the remote object's identifier from a webhook payload.
        
        Parameters:
            payload (dict[str, Any]): Webhook event payload.
        
        Returns:
            str: The remote object's identifier extracted from the payload.
        """
        pass

    @abstractmethod
    def _extract_remote_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Extract the remote object data from a webhook payload.
        
        If the payload contains an "issue" key (ITSM-style payloads), returns the value of that key; otherwise returns the payload unchanged.
        
        Parameters:
            payload (dict[str, Any]): The webhook payload.
        
        Returns:
            dict[str, Any]: The remote object data to be mapped to local fields.
        """
        pass

    def _get_or_create_mapping(self, local_object: models.Model) -> SyncMapping:
        """
        Retrieve the SyncMapping for a local Django model instance, creating one if it does not exist.
        
        If a new mapping is created its `sync_status` is initialized to `SyncMapping.SyncStatus.PENDING` and `version` to 1; creation is logged.
        
        Returns:
            SyncMapping: The mapping instance corresponding to the provided local object.
        """
        from .models import SyncMapping

        content_type = ContentType.objects.get_for_model(local_object)
        mapping, created = SyncMapping.objects.get_or_create(
            configuration=self.configuration,
            content_type=content_type,
            local_object_id=local_object.pk,
            defaults={
                "sync_status": SyncMapping.SyncStatus.PENDING,
                "version": 1,
            },
        )

        if created:
            logger.info(
                f"Created new mapping for {content_type.model} {local_object.pk}"
            )

        return mapping

    def _get_local_object(self, mapping: SyncMapping) -> AbstractBaseModel:
        """
        Retrieve the local Django model instance referenced by a SyncMapping.
        
        Parameters:
            mapping (SyncMapping): Mapping containing the ContentType and local_object_id that identify the local model instance.
        
        Returns:
            AbstractBaseModel: The local model instance corresponding to mapping.local_object_id.
        
        Raises:
            DoesNotExist: If no local object exists for the given primary key.
        """
        # Use the ContentType to get the correct model
        Model = mapping.content_type.model_class()
        return Model.objects.get(pk=mapping.local_object_id)

    def _update_local_object(
        self, local_object: models.Model, local_data: dict[str, Any]
    ) -> None:
        """
        Update attributes on a Django model instance from a mapping and persist changes without triggering sync handlers.
        
        Parameters:
        	local_object (models.Model): The model instance to update.
        	local_data (dict[str, Any]): Mapping of attribute names to values to set on the instance.
        """
        for field, value in local_data.items():
            setattr(local_object, field, value)

        # Save with skip_sync flag to prevent infinite loop
        local_object.save(skip_sync=True)
        logger.debug(
            f"Updated local object {local_object.pk} with fields: {list(local_data.keys())}"
        )

    def _has_conflict(self, mapping: SyncMapping, remote_data: dict[str, Any]) -> bool:
        """
        Determine whether the local object and incoming remote data are in conflict.
        
        A conflict occurs when the local object's updated_at is later than the mapping's last_synced_at and the incoming remote_data is different from the mapping's cached remote_data.
        
        Returns:
            `true` if a conflict exists, `false` otherwise.
        """
        # Simple version-based conflict detection
        # You can override this for more sophisticated conflict detection
        local_object = self._get_local_object(mapping)

        # Check if local object was modified recently
        if hasattr(local_object, "updated_at"):
            # Compare local object's last update to the mapping's last sync
            if local_object.updated_at > mapping.last_synced_at:
                # Local changes exist, check if remote also changed
                if mapping.remote_data != remote_data:
                    return True

        return False

    def _resolve_conflict(
        self, mapping: SyncMapping, remote_data: dict[str, Any]
    ) -> bool:
        """
        Resolve a detected conflict between the local object and remote data according to the integration's conflict resolution setting.
        
        When invoked, this method applies one of three configured strategies:
        - "remote_wins": overwrite the local object with `remote_data` and mark the mapping as synced.
        - "local_wins": push the local object's data to the remote system and mark the mapping as synced.
        - "manual": mark the mapping as in conflict and require manual intervention.
        
        Parameters:
            mapping (SyncMapping): The SyncMapping record linking the local object and remote resource.
            remote_data (dict[str, Any]): The remote object's representation used to resolve the conflict.
        
        Returns:
            bool: `True` if the conflict was resolved automatically ("remote_wins" or "local_wins"), `False` if manual resolution is required or no action was taken.
        """
        conflict_resolution = self.configuration.settings.get(
            "conflict_resolution", "remote_wins"
        )

        if conflict_resolution == "remote_wins":
            logger.info(f"Resolving conflict for mapping {mapping.id}: remote wins")
            local_data = self.mapper.to_local(remote_data)
            local_object = self._get_local_object(mapping)
            self._update_local_object(local_object, local_data)

            mapping.sync_status = SyncMapping.SyncStatus.SYNCED
            mapping.remote_data = remote_data
            mapping.version += 1
            mapping.save()
            return True

        elif conflict_resolution == "local_wins":
            logger.info(f"Resolving conflict for mapping {mapping.id}: local wins")
            local_object = self._get_local_object(mapping)
            remote_changes = self.mapper.to_remote(local_object)
            self.client.update_remote_object(mapping.remote_id, remote_changes)

            mapping.sync_status = SyncMapping.SyncStatus.SYNCED
            mapping.remote_data = remote_data
            mapping.version += 1
            mapping.save()
            return True

        elif conflict_resolution == "manual":
            logger.info(f"Conflict for mapping {mapping.id} requires manual resolution")
            mapping.sync_status = "conflict"
            mapping.save()
            return False

        return False

    def _handle_remote_deletion(self, remote_id: str) -> bool:
        """
        Handle deletion of a remote object and update the corresponding SyncMapping.
        
        By default this marks the mapping as failed with an explanatory error message; subclasses may override to implement alternative behaviors (for example deleting the local object or archiving it).
        
        Returns:
            bool: `True` if a mapping was found and handled, `False` otherwise.
        """
        from .models import SyncMapping

        try:
            mapping = SyncMapping.objects.get(
                configuration=self.configuration, remote_id=remote_id
            )

            # Option 1: Mark as failed
            mapping.sync_status = SyncMapping.SyncStatus.FAILED
            mapping.error_message = "Remote object was deleted"
            mapping.save()

            # Option 2: Delete the local object (use with caution!)
            # local_object = self._get_local_object(mapping)
            # local_object.delete() # This will delete the mapping via CASCADE

            # Option 3: Set local object to a 'deprecated' or 'archived' status
            # local_object = self._get_local_object(mapping)
            # local_object.status = "deprecated"
            # local_object.save(skip_sync=True)
            # mapping.delete() # Remove the mapping

            logger.info(
                f"Remote object {remote_id} was deleted. Marked mapping {mapping.id} as failed."
            )
            return True

        except SyncMapping.DoesNotExist:
            logger.warning(f"No mapping found for deleted remote object {remote_id}")
            return False

    def _log_sync_event(
        self,
        mapping: SyncMapping,
        direction: str,
        changed_fields: list[str],
        success: bool,
        error: str = "",
    ) -> None:
        """
        Create a SyncEvent audit record for a synchronization attempt.
        
        Creates a SyncEvent with the given mapping and direction, records the changed fields under the `changes` payload as {"fields": changed_fields}, records the success flag and any error details, and sets `triggered_by` to `SyncEvent.TriggeredBy.WEBHOOK` when `direction == SyncMapping.SyncDirection.PULL`, otherwise to "system".
        
        Parameters:
            mapping (SyncMapping): The SyncMapping linking the local and remote objects.
            direction (str): The sync direction (e.g., pull or push).
            changed_fields (list[str]): Names of fields that changed.
            success (bool): True if the sync succeeded, False otherwise.
            error (str): Optional error details to record.
        """
        from .models import SyncEvent

        SyncEvent.objects.create(
            mapping=mapping,
            direction=direction,
            changes={"fields": changed_fields},
            triggered_by=SyncEvent.TriggeredBy.WEBHOOK
            if direction == SyncMapping.SyncDirection.PULL
            else "system",
            success=success,
            error_details=error,
        )


class BaseITSMOrchestrator(BaseSyncOrchestrator):
    """Base orchestrator specifically for ITSM integrations

    Provides common ITSM-specific functionality
    """

    def _extract_remote_id(self, payload: dict[str, Any]) -> str:
        """
        Extract the remote issue identifier (issue key) from an ITSM webhook payload.
        
        Parameters:
            payload (dict[str, Any]): Webhook payload potentially containing an "issue" object.
        
        Returns:
            str | None: The issue key if present (e.g., "PROJ-1"), otherwise `None`.
        """
        # Jira payload: { ..., "issue": { "id": "10001", "key": "PROJ-1" } }
        issue = payload.get("issue", {})
        return issue.get("key")

    def _extract_remote_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Extract the remote issue data from an ITSM webhook payload.
        
        Returns:
            dict[str, Any]: The nested `issue` object when present; otherwise the original `payload`.
        """
        # We pass the whole 'issue' object, as mappers may need 'id' or 'key'
        # as well as the 'fields' dictionary.
        if "issue" in payload:
            return payload["issue"]
        return payload