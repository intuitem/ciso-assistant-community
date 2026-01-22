"""
Audit Log Aggregate

Comprehensive audit trail for all RMF operations to support
compliance requirements and user activity tracking.
"""

import uuid
from typing import Optional, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class AuditLog(AggregateRoot):
    """
    Audit log for RMF operations.

    Tracks all changes to RMF data for compliance and audit purposes.
    """

    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('import_ckl', 'Import CKL'),
        ('export_ckl', 'Export CKL'),
        ('bulk_update', 'Bulk Update'),
        ('compliance_check', 'Compliance Check'),
        ('activate', 'Activate'),
        ('archive', 'Archive'),
        ('assign_system', 'Assign to System'),
        ('remove_from_system', 'Remove from System'),
    ]

    ENTITY_TYPES = [
        ('system_group', 'System Group'),
        ('stig_checklist', 'STIG Checklist'),
        ('vulnerability_finding', 'Vulnerability Finding'),
        ('checklist_score', 'Checklist Score'),
        ('nessus_scan', 'Nessus Scan'),
    ]

    user_id = models.UUIDField(help_text="User who performed the action")
    username = models.CharField(max_length=150, help_text="Username for display purposes")

    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        help_text="Type of action performed"
    )

    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPES,
        help_text="Type of entity affected"
    )

    entity_id = models.UUIDField(help_text="ID of the affected entity")
    entity_name = models.CharField(
        max_length=255,
        help_text="Human-readable entity name/title"
    )

    # Change tracking
    old_values = models.JSONField(
        null=True,
        blank=True,
        help_text="Previous values before the change"
    )
    new_values = models.JSONField(
        null=True,
        blank=True,
        help_text="New values after the change"
    )

    # Request context (optional)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user"
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="User agent string from the request"
    )

    # Additional metadata
    session_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Session identifier"
    )
    correlation_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Request correlation ID"
    )

    # Success/failure tracking
    success = models.BooleanField(
        default=True,
        help_text="Whether the operation was successful"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if operation failed"
    )

    class Meta:
        db_table = "rmf_operations_audit_logs"
        indexes = [
            models.Index(fields=['user_id'], name='rmf_audit_user_idx'),
            models.Index(fields=['entity_type', 'entity_id'], name='rmf_audit_entity_idx'),
            models.Index(fields=['action_type'], name='rmf_audit_action_idx'),
            models.Index(fields=['created_at'], name='rmf_audit_created_idx'),
            models.Index(fields=['success'], name='rmf_audit_success_idx'),
            models.Index(fields=['correlation_id'], name='rmf_audit_correlation_idx'),
        ]
        ordering = ['-created_at']

    def create_log_entry(
        self,
        user_id: uuid.UUID,
        username: str,
        action_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        entity_name: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Create a new audit log entry"""
        self.user_id = user_id
        self.username = username
        self.action_type = action_type
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.old_values = old_values
        self.new_values = new_values
        self.success = success
        self.error_message = error_message

        # Extract request context if provided
        if request_context:
            self.ip_address = request_context.get('ip_address')
            self.user_agent = request_context.get('user_agent')
            self.session_id = request_context.get('session_id')
            self.correlation_id = request_context.get('correlation_id')

        self.created_by = user_id
        self.updated_by = user_id

    @classmethod
    def log_action(
        cls,
        user_id: uuid.UUID,
        username: str,
        action_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        entity_name: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> 'AuditLog':
        """Class method to create and save an audit log entry"""
        audit_log = cls()
        audit_log.create_log_entry(
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
        audit_log.save()
        return audit_log

    def __str__(self):
        return f"AuditLog({self.action_type} {self.entity_type} by {self.username})"
