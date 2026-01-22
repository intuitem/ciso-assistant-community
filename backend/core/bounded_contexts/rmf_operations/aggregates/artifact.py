"""
Artifact Aggregate

Aggregate for managing file attachments, evidence, and supporting documentation
in the RMF compliance process. Provides secure file storage and metadata management.
"""

import uuid
import os
from typing import Optional, List, Dict, Any
from django.db import models
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class Artifact(AggregateRoot):
    """
    Artifact aggregate for file attachments and evidence management.

    Stores files, screenshots, and supporting documentation related to
    RMF compliance activities, vulnerability findings, and assessments.
    """

    # File information
    filename = models.CharField(
        max_length=255,
        help_text="Original filename"
    )
    file_path = models.CharField(
        max_length=500,
        unique=True,
        help_text="Internal file path for storage"
    )
    file_size = models.BigIntegerField(
        help_text="File size in bytes"
    )

    # File metadata
    content_type = models.CharField(
        max_length=100,
        help_text="MIME content type"
    )
    file_hash = models.CharField(
        max_length=128,
        help_text="SHA-256 hash of file content"
    )

    # Artifact classification
    ARTIFACT_TYPES = [
        ('screenshot', 'Screenshot'),
        ('document', 'Document'),
        ('evidence', 'Evidence'),
        ('configuration', 'Configuration File'),
        ('log', 'Log File'),
        ('report', 'Report'),
        ('certificate', 'Certificate'),
        ('other', 'Other'),
    ]

    artifact_type = models.CharField(
        max_length=20,
        choices=ARTIFACT_TYPES,
        default='other',
        help_text="Type of artifact"
    )

    # Description and context
    title = models.CharField(
        max_length=255,
        help_text="Artifact title"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Artifact description and context"
    )

    # Relationships
    system_group_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Associated system group"
    )

    checklist_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Associated STIG checklist"
    )

    vulnerability_finding_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Associated vulnerability finding"
    )

    nessus_scan_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Associated Nessus scan"
    )

    # RMF context
    control_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Associated RMF control (e.g., AC-2, IA-5)"
    )

    cci_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Associated CCI IDs"
    )

    # Security classification
    SECURITY_LEVELS = [
        ('public', 'Public'),
        ('internal', 'Internal Use'),
        ('confidential', 'Confidential'),
        ('restricted', 'Restricted'),
    ]

    security_level = models.CharField(
        max_length=15,
        choices=SECURITY_LEVELS,
        default='internal',
        help_text="Security classification level"
    )

    # Access control
    is_public = models.BooleanField(
        default=False,
        help_text="Whether artifact is publicly accessible"
    )

    access_list = models.JSONField(
        default=list,
        blank=True,
        help_text="List of users/groups with access (if not public)"
    )

    # Status and lifecycle
    is_active = models.BooleanField(
        default=True,
        help_text="Whether artifact is active/available"
    )

    retention_period_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Retention period in days (null = indefinite)"
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration date for automatic cleanup"
    )

    # Tags and organization
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Artifact tags for organization"
    )

    # Metadata
    source = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Source of the artifact (e.g., 'manual_upload', 'nessus_scan')"
    )

    version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Artifact version or revision"
    )

    class Meta:
        db_table = "rmf_operations_artifacts"
        indexes = [
            models.Index(fields=['system_group_id'], name='rmf_artifact_sysgrp_idx'),
            models.Index(fields=['checklist_id'], name='rmf_artifact_checklist_idx'),
            models.Index(fields=['vulnerability_finding_id'], name='rmf_artifact_finding_idx'),
            models.Index(fields=['nessus_scan_id'], name='rmf_artifact_scan_idx'),
            models.Index(fields=['artifact_type', 'is_active'], name='rmf_artifact_type_active_idx'),
            models.Index(fields=['control_id'], name='rmf_artifact_control_idx'),
            models.Index(fields=['expires_at'], name='rmf_artifact_expires_idx'),
            models.Index(fields=['security_level'], name='rmf_artifact_security_idx'),
        ]
        ordering = ['-created_at']

    def create_artifact(
        self,
        filename: str,
        file_content: bytes,
        content_type: str,
        title: str,
        artifact_type: str = 'other',
        description: Optional[str] = None,
        system_group_id: Optional[uuid.UUID] = None,
        checklist_id: Optional[uuid.UUID] = None,
        vulnerability_finding_id: Optional[uuid.UUID] = None,
        nessus_scan_id: Optional[uuid.UUID] = None,
        control_id: Optional[str] = None,
        security_level: str = 'internal',
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        retention_period_days: Optional[int] = None
    ):
        """Create a new artifact with file storage"""
        import hashlib

        # Generate file hash
        self.file_hash = hashlib.sha256(file_content).hexdigest()

        # Set basic properties
        self.filename = filename
        self.file_size = len(file_content)
        self.content_type = content_type
        self.title = title
        self.artifact_type = artifact_type
        self.description = description
        self.system_group_id = system_group_id
        self.checklist_id = checklist_id
        self.vulnerability_finding_id = vulnerability_finding_id
        self.nessus_scan_id = nessus_scan_id
        self.control_id = control_id
        self.security_level = security_level
        self.tags = tags if tags is not None else []
        self.source = source

        # Generate unique file path
        file_extension = os.path.splitext(filename)[1]
        self.file_path = f"rmf_artifacts/{self.id}{file_extension}"

        # Store file
        try:
            default_storage.save(self.file_path, ContentFile(file_content))
        except Exception as e:
            raise ValueError(f"Failed to store file: {str(e)}")

        # Set retention
        if retention_period_days:
            self.retention_period_days = retention_period_days
            self.expires_at = timezone.now() + timezone.timedelta(days=retention_period_days)

        from ..domain_events import ArtifactCreated
        self._raise_event(ArtifactCreated(
            aggregate_id=self.id,
            filename=filename,
            artifact_type=artifact_type,
            file_size=self.file_size
        ))

    def update_metadata(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        artifact_type: Optional[str] = None,
        control_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Update artifact metadata"""
        old_metadata = {
            'title': self.title,
            'description': self.description,
            'artifact_type': self.artifact_type,
            'control_id': self.control_id,
            'tags': self.tags.copy()
        }

        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if artifact_type is not None:
            self.artifact_type = artifact_type
        if control_id is not None:
            self.control_id = control_id
        if tags is not None:
            self.tags = tags

        from ..domain_events import ArtifactMetadataUpdated
        self._raise_event(ArtifactMetadataUpdated(
            aggregate_id=self.id,
            old_metadata=old_metadata,
            new_metadata={
                'title': self.title,
                'description': self.description,
                'artifact_type': self.artifact_type,
                'control_id': self.control_id,
                'tags': self.tags
            }
        ))

    def add_relationship(
        self,
        checklist_id: Optional[uuid.UUID] = None,
        vulnerability_finding_id: Optional[uuid.UUID] = None,
        nessus_scan_id: Optional[uuid.UUID] = None
    ):
        """Add relationship to RMF entities"""
        if checklist_id:
            self.checklist_id = checklist_id
        if vulnerability_finding_id:
            self.vulnerability_finding_id = vulnerability_finding_id
        if nessus_scan_id:
            self.nessus_scan_id = nessus_scan_id

        from ..domain_events import ArtifactRelationshipAdded
        self._raise_event(ArtifactRelationshipAdded(
            aggregate_id=self.id,
            relationships={
                'checklist_id': str(checklist_id) if checklist_id else None,
                'vulnerability_finding_id': str(vulnerability_finding_id) if vulnerability_finding_id else None,
                'nessus_scan_id': str(nessus_scan_id) if nessus_scan_id else None,
            }
        ))

    def add_cci_reference(self, cci_id: str):
        """Add CCI reference"""
        if cci_id not in self.cci_ids:
            self.cci_ids.append(cci_id)

            from ..domain_events import ArtifactCCIAdded
            self._raise_event(ArtifactCCIAdded(
                aggregate_id=self.id,
                cci_id=cci_id
            ))

    def set_security_level(self, security_level: str, access_list: Optional[List[str]] = None):
        """Update security classification"""
        old_level = self.security_level
        old_access = self.access_list.copy()

        self.security_level = security_level
        if access_list is not None:
            self.access_list = access_list

        from ..domain_events import ArtifactSecurityUpdated
        self._raise_event(ArtifactSecurityUpdated(
            aggregate_id=self.id,
            old_security_level=old_level,
            new_security_level=security_level,
            old_access_list=old_access,
            new_access_list=self.access_list
        ))

    def deactivate(self):
        """Deactivate artifact"""
        if self.is_active:
            self.is_active = False

            from ..domain_events import ArtifactDeactivated
            self._raise_event(ArtifactDeactivated(
                aggregate_id=self.id,
                filename=self.filename
            ))

    def delete_file(self):
        """Delete the physical file"""
        try:
            if default_storage.exists(self.file_path):
                default_storage.delete(self.file_path)
        except Exception:
            # Log but don't fail - file might already be deleted
            pass

    def is_expired(self) -> bool:
        """Check if artifact has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def file_url(self) -> Optional[str]:
        """Get file URL for access"""
        try:
            return default_storage.url(self.file_path)
        except Exception:
            return None

    @property
    def human_readable_size(self) -> str:
        """Get human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def __str__(self):
        return f"Artifact({self.filename} - {self.artifact_type} - {self.human_readable_size})"
