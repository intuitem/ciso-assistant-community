"""
Repository Pattern

Repositories abstract the persistence layer and provide
a collection-like interface for aggregates.
"""

from typing import Generic, TypeVar, Optional, List, Type
from uuid import UUID
from django.db import models
from .aggregate import AggregateRoot

T = TypeVar('T', bound=AggregateRoot)


class Repository(Generic[T]):
    """
    Base repository interface.
    
    Repositories provide a collection-like interface for aggregates,
    abstracting away the persistence details.
    """
    
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class
    
    def get_by_id(self, id: UUID) -> Optional[T]:
        """Get aggregate by ID"""
        try:
            return self.model_class.objects.get(id=id)
        except self.model_class.DoesNotExist:
            return None
    
    def get_all(self) -> List[T]:
        """Get all aggregates"""
        return list(self.model_class.objects.all())
    
    def save(self, aggregate: T) -> T:
        """Save aggregate (creates or updates)"""
        aggregate.save()
        return aggregate
    
    def delete(self, aggregate: T):
        """Delete aggregate"""
        aggregate.delete()
    
    def exists(self, id: UUID) -> bool:
        """Check if aggregate exists"""
        return self.model_class.objects.filter(id=id).exists()
    
    def count(self) -> int:
        """Get count of aggregates"""
        return self.model_class.objects.count()


class BaseRepository(Repository[T]):
    """
    Base repository with audit logging capabilities.

    Extends the basic Repository with audit logging for RMF operations.
    """

    def __init__(self, model_class: Type[T]):
        super().__init__(model_class)

    def save(self, aggregate: T, user_id: Optional[UUID] = None,
             username: Optional[str] = None, request=None) -> T:
        """
        Save aggregate with audit logging.

        Args:
            aggregate: The aggregate to save
            user_id: ID of the user performing the action
            username: Username for audit logging
            request: HTTP request for context

        Returns:
            The saved aggregate
        """
        # Determine if this is a create or update operation
        is_new = aggregate._state.adding

        # Store old values for audit logging (for updates)
        old_values = None
        if not is_new:
            try:
                # Get the existing instance from database
                existing = self.model_class.objects.get(id=aggregate.id)
                old_values = self._get_audit_values(existing)
            except self.model_class.DoesNotExist:
                # If it doesn't exist, treat as new
                is_new = True

        # Perform the save
        aggregate = super().save(aggregate)

        # Log the operation if user context is provided
        if user_id and username:
            self._log_operation(
                aggregate, is_new, user_id, username,
                old_values, request
            )

        return aggregate

    def _get_audit_values(self, aggregate: T) -> dict:
        """Extract values for audit logging from aggregate"""
        # Default implementation - override in subclasses for specific fields
        values = {}
        audit_fields = [
            'title', 'name', 'description', 'lifecycle_state',
            'stig_type', 'stig_release', 'version', 'host_name'
        ]

        for field in audit_fields:
            if hasattr(aggregate, field):
                value = getattr(aggregate, field)
                if value is not None:
                    values[field] = str(value)

        return values

    def _log_operation(self, aggregate: T, is_new: bool, user_id: UUID,
                      username: str, old_values: Optional[dict], request):
        """Log the operation to audit service"""
        try:
            from ..bounded_contexts.rmf_operations.services.audit_service import audit_service

            action_type = 'create' if is_new else 'update'
            entity_type = self._get_entity_type()
            entity_name = self._get_entity_name(aggregate)
            new_values = self._get_audit_values(aggregate)

            audit_service.log_operation(
                user_id=user_id,
                username=username,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=aggregate.id,
                entity_name=entity_name,
                request=request,
                old_values=old_values if not is_new else None,
                new_values=new_values if not is_new else new_values,
                success=True
            )
        except Exception as e:
            # Log error but don't fail the operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log audit operation: {str(e)}")

    def _get_entity_type(self) -> str:
        """Get entity type name for audit logging"""
        # Default mapping - subclasses can override
        class_name = self.model_class.__name__.lower()
        mappings = {
            'systemgroup': 'system_group',
            'stigchecklist': 'stig_checklist',
            'vulnerabilityfinding': 'vulnerability_finding',
            'checklistscore': 'checklist_score',
            'auditlog': 'audit_log'
        }
        return mappings.get(class_name, class_name)

    def _get_entity_name(self, aggregate: T) -> str:
        """Get human-readable entity name for audit logging"""
        # Try common name fields
        for field in ['title', 'name', 'host_name', 'vuln_id']:
            if hasattr(aggregate, field):
                value = getattr(aggregate, field)
                if value:
                    return str(value)

        # Fallback to class name and ID
        return f"{self.model_class.__name__} {aggregate.id}"

