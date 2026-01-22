"""
Audit Service

Service for logging RMF operations to support compliance requirements
and user activity tracking.
"""

import uuid
import logging
from typing import Optional, Dict, Any

from django.utils import timezone
from django.http import HttpRequest

from ..aggregates.audit_log import AuditLog
from ..repositories.audit_log_repository import AuditLogRepository

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for logging RMF operations.

    Provides a centralized way to log all RMF operations for compliance,
    auditing, and user activity tracking.
    """

    def __init__(self):
        self.repository = AuditLogRepository()

    def log_operation(
        self,
        user_id: uuid.UUID,
        username: str,
        action_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        entity_name: str,
        request: Optional[HttpRequest] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Log an RMF operation.

        Args:
            user_id: ID of the user performing the action
            username: Username for display purposes
            action_type: Type of action (create, update, delete, etc.)
            entity_type: Type of entity affected
            entity_id: ID of the affected entity
            entity_name: Human-readable name of the entity
            request: HTTP request object for context (optional)
            old_values: Previous values before change (optional)
            new_values: New values after change (optional)
            success: Whether the operation was successful
            error_message: Error message if operation failed

        Returns:
            The created AuditLog instance
        """
        try:
            # Extract request context if available
            request_context = None
            if request:
                request_context = self._extract_request_context(request)

            # Create and save audit log
            audit_log = AuditLog.log_action(
                user_id=user_id,
                username=username,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                old_values=old_values,
                new_values=new_values,
                request_context=request_context,
                success=success,
                error_message=error_message
            )

            logger.info(f"Audit log created: {action_type} {entity_type} '{entity_name}' by {username}")

            return audit_log

        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            # Don't raise exception - audit logging should not break business logic
            return None

    def log_bulk_operation(
        self,
        user_id: uuid.UUID,
        username: str,
        action_type: str,
        entity_type: str,
        entity_ids: list[uuid.UUID],
        entity_names: list[str],
        request: Optional[HttpRequest] = None,
        summary_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> list[AuditLog]:
        """
        Log a bulk operation affecting multiple entities.

        Args:
            user_id: ID of the user performing the action
            username: Username for display purposes
            action_type: Type of bulk action
            entity_type: Type of entities affected
            entity_ids: List of entity IDs affected
            entity_names: List of entity names (should match entity_ids length)
            request: HTTP request object for context (optional)
            summary_data: Summary of the bulk operation
            success: Whether the operation was successful
            error_message: Error message if operation failed

        Returns:
            List of created AuditLog instances
        """
        audit_logs = []

        try:
            # Extract request context if available
            request_context = None
            if request:
                request_context = self._extract_request_context(request)

            # Create individual audit logs for each entity
            for entity_id, entity_name in zip(entity_ids, entity_names):
                audit_log = AuditLog.log_action(
                    user_id=user_id,
                    username=username,
                    action_type=action_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    old_values=None,  # Bulk operations may not have individual old/new values
                    new_values=summary_data,
                    request_context=request_context,
                    success=success,
                    error_message=error_message
                )
                audit_logs.append(audit_log)

            logger.info(f"Bulk audit logs created: {len(audit_logs)} entries for {action_type}")

        except Exception as e:
            logger.error(f"Failed to create bulk audit logs: {str(e)}")

        return audit_logs

    def log_system_operation(
        self,
        action_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        entity_name: str,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        Log a system-level operation (not initiated by a specific user).

        Args:
            action_type: Type of action
            entity_type: Type of entity affected
            entity_id: ID of the affected entity
            entity_name: Human-readable name of the entity
            details: Additional operation details
            success: Whether the operation was successful
            error_message: Error message if operation failed

        Returns:
            The created AuditLog instance or None if failed
        """
        try:
            # Use system user ID (you might want to define this as a constant)
            system_user_id = uuid.UUID('00000000-0000-0000-0000-000000000000')
            system_username = 'System'

            audit_log = AuditLog.log_action(
                user_id=system_user_id,
                username=system_username,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                old_values=None,
                new_values=details,
                request_context=None,
                success=success,
                error_message=error_message
            )

            logger.info(f"System audit log created: {action_type} {entity_type} '{entity_name}'")

            return audit_log

        except Exception as e:
            logger.error(f"Failed to create system audit log: {str(e)}")
            return None

    def _extract_request_context(self, request: HttpRequest) -> Dict[str, Any]:
        """Extract context information from HTTP request"""
        context = {}

        # IP address
        context['ip_address'] = self._get_client_ip(request)

        # User agent
        context['user_agent'] = request.META.get('HTTP_USER_AGENT')

        # Session ID (if using Django sessions)
        if hasattr(request, 'session') and request.session.session_key:
            context['session_id'] = request.session.session_key

        # Correlation ID (if set in headers or middleware)
        correlation_id = (
            request.META.get('HTTP_X_CORRELATION_ID') or
            request.META.get('HTTP_X_REQUEST_ID')
        )
        if correlation_id:
            context['correlation_id'] = correlation_id

        return context

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get the client's IP address from the request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP if there are multiple
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'

    # Convenience methods for common operations

    def log_create(self, user_id: uuid.UUID, username: str, entity_type: str,
                  entity_id: uuid.UUID, entity_name: str, request: Optional[HttpRequest] = None) -> Optional[AuditLog]:
        """Log entity creation"""
        return self.log_operation(user_id, username, 'create', entity_type, entity_id, entity_name, request)

    def log_update(self, user_id: uuid.UUID, username: str, entity_type: str,
                  entity_id: uuid.UUID, entity_name: str, old_values: Dict[str, Any],
                  new_values: Dict[str, Any], request: Optional[HttpRequest] = None) -> Optional[AuditLog]:
        """Log entity update"""
        return self.log_operation(
            user_id, username, 'update', entity_type, entity_id, entity_name,
            request, old_values, new_values
        )

    def log_delete(self, user_id: uuid.UUID, username: str, entity_type: str,
                  entity_id: uuid.UUID, entity_name: str, request: Optional[HttpRequest] = None) -> Optional[AuditLog]:
        """Log entity deletion"""
        return self.log_operation(user_id, username, 'delete', entity_type, entity_id, entity_name, request)

    def log_import_ckl(self, user_id: uuid.UUID, username: str, checklist_id: uuid.UUID,
                       checklist_name: str, request: Optional[HttpRequest] = None) -> Optional[AuditLog]:
        """Log CKL import operation"""
        return self.log_operation(
            user_id, username, 'import_ckl', 'stig_checklist',
            checklist_id, checklist_name, request
        )

    def log_bulk_status_update(self, user_id: uuid.UUID, username: str, finding_ids: list[uuid.UUID],
                              finding_names: list[str], new_status: str,
                              request: Optional[HttpRequest] = None) -> list[AuditLog]:
        """Log bulk vulnerability status update"""
        return self.log_bulk_operation(
            user_id, username, 'bulk_update', 'vulnerability_finding',
            finding_ids, finding_names, request, {'new_status': new_status}
        )


# Global audit service instance
audit_service = AuditService()
