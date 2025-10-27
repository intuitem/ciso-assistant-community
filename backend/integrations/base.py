import logging
from abc import ABC, abstractmethod
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db import models

from core.base_models import AbstractBaseModel
from integrations.models import IntegrationConfiguration, SyncMapping

logger = logging.getLogger(__name__)


class BaseIntegrationClient(ABC):
    """Base class for all integration clients"""

    def __init__(self, configuration: IntegrationConfiguration):
        self.configuration = configuration
        self.credentials = configuration.credentials
        self.settings = configuration.settings

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if credentials are valid"""
        pass

    @abstractmethod
    def create_remote_object(self, local_object) -> str:
        """Create object in remote system, return remote ID"""
        pass

    @abstractmethod
    def update_remote_object(self, remote_id: str, changes: dict[str, Any]) -> bool:
        """Update object in remote system"""
        pass

    @abstractmethod
    def get_remote_object(self, remote_id: str) -> dict[str, Any]:
        """Fetch object from remote system"""
        pass

    @abstractmethod
    def list_remote_objects(
        self, query_params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """List objects from remote system based on query parameters"""
        pass

    @abstractmethod
    def register_webhook(self, callback_url: str) -> dict[str, Any]:
        """Register webhook with remote system"""
        pass

    @abstractmethod
    def unregister_webhook(self, webhook_id: str) -> bool:
        """Unregister webhook from remote system"""
        pass


class BaseFieldMapper(ABC):
    """Maps fields between local and remote systems"""

    # Define field mappings as class attributes
    # Format: {'local_field': 'remote_field'}
    FIELD_MAPPINGS: dict[str, str] = {}

    def __init__(self, configuration: IntegrationConfiguration):
        self.configuration = configuration
        # Allow per-instance custom mappings
        self.custom_mappings = configuration.settings.get("field_mappings", {})

    def to_remote(self, local_object: models.Model) -> dict[str, Any]:
        """Convert local object to remote format (all fields)"""
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
        """Convert only specific fields to remote format"""
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
        """Convert remote data to local format"""
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
        """Combine class-level and instance-level mappings"""
        return {**self.FIELD_MAPPINGS, **self.custom_mappings}

    def _get_local_value(self, local_object: models.Model, field_name: str) -> Any:
        """Get value from local object, handling nested attributes"""
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
        """Get value from remote data, handling nested attributes"""
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
        """Transform specific field values for remote system

        Args:
            field: Local field name
            value: Local field value

        Returns:
            Transformed value suitable for remote system, or None to skip
        """
        pass

    @abstractmethod
    def _transform_value_to_local(self, field: str, value: Any) -> Any:
        """Transform specific field values from remote system

        Args:
            field: Local field name
            value: Remote field value

        Returns:
            Transformed value suitable for local system, or None to skip
        """
        pass


class BaseSyncOrchestrator:
    """Orchestrates sync operations between local and remote systems"""

    def __init__(self, configuration: IntegrationConfiguration):
        self.configuration = configuration
        self.client = self._get_client()
        self.mapper = self._get_mapper()

    @abstractmethod
    def _get_client(self) -> BaseIntegrationClient:
        """Return the appropriate client for this integration"""
        pass

    @abstractmethod
    def _get_mapper(self) -> BaseFieldMapper:
        """Return the appropriate field mapper for this integration"""
        pass

    def push_changes(
        self, local_object: models.Model, changed_fields: list[str]
    ) -> bool:
        """Push local changes to remote system

        Args:
            local_object: The Django model instance that changed
            changed_fields: list of field names that changed

        Returns:
            True if sync succeeded, False otherwise
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
                remote_data = self.mapper.to_remote(local_object)
                remote_id = self.client.create_remote_object(local_object)
                mapping.remote_id = remote_id
                logger.info(f"Created remote object {remote_id}")

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
        """Pull changes from remote system to local object

        Args:
            remote_id: Remote object identifier
            remote_data: Current remote object data

        Returns:
            True if sync succeeded, False otherwise
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
                logger.warning(f"Conflict detected for mapping {mapping.id}")
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
        """Handle incoming webhook event

        Args:
            event_type: Type of event (e.g., 'issue_updated', 'issue_created')
            payload: Webhook payload

        Returns:
            True if event was handled successfully
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
        """Extract remote object ID from webhook payload"""
        pass

    @abstractmethod
    def _extract_remote_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract remote object data from webhook payload"""
        pass

    def _get_or_create_mapping(self, local_object: models.Model) -> SyncMapping:
        """Get or create SyncMapping for local object"""
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
        """Get local Django model instance from mapping"""
        # Use the ContentType to get the correct model
        Model = mapping.content_type.model_class()
        return Model.objects.get(pk=mapping.local_object_id)

    def _update_local_object(
        self, local_object: models.Model, local_data: dict[str, Any]
    ) -> None:
        """Update local object with data, skipping sync trigger"""
        for field, value in local_data.items():
            setattr(local_object, field, value)

        # Save with skip_sync flag to prevent infinite loop
        # This assumes your AppliedControl.save() method checks for 'skip_sync'
        local_object.save(skip_sync=True)
        logger.debug(
            f"Updated local object {local_object.pk} with fields: {list(local_data.keys())}"
        )

    def _has_conflict(self, mapping: SyncMapping, remote_data: dict[str, Any]) -> bool:
        """Check if there's a conflict between local and remote changes

        A conflict exists if:
        1. Local object was modified since last sync (version mismatch)
        2. Remote data differs from cached remote_data
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
        """Resolve conflict between local and remote changes

        Default strategy: Remote wins (last-write-wins from remote side)
        Override this method to implement different conflict resolution strategies
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
        """Handle deletion of remote object

        Default behavior: Mark mapping as failed
        Override to implement custom deletion handling
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
        """Create audit log entry for sync operation"""
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
        """Most ITSM systems use 'key' or 'id' for issue identifier"""
        # Jira payload: { ..., "issue": { "id": "10001", "key": "PROJ-1" } }
        issue = payload.get("issue", {})
        return issue.get("key")

    def _extract_remote_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Most ITSM systems nest data under 'issue' or 'fields'"""
        # We pass the whole 'issue' object, as mappers may need 'id' or 'key'
        # as well as the 'fields' dictionary.
        if "issue" in payload:
            return payload["issue"]
        return payload
