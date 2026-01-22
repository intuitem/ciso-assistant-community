"""
Nessus Scan Aggregate

Aggregate for storing and managing Nessus ACAS vulnerability scan files.
Provides comprehensive Nessus scan data management with metadata extraction
and correlation capabilities.
"""

import uuid
from typing import Optional, Dict, Any, List
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField


class NessusScan(AggregateRoot):
    """
    Nessus ACAS scan file storage and management.

    Stores raw Nessus XML files and provides metadata extraction,
    vulnerability correlation, and reporting capabilities.
    """

    systemGroupId = models.UUIDField(
        db_index=True,
        help_text="Associated system group for this scan"
    )

    # File information
    filename = models.CharField(
        max_length=255,
        help_text="Original Nessus scan filename"
    )
    raw_xml_content = models.TextField(
        help_text="Complete raw Nessus XML scan data"
    )

    # Scan metadata (extracted from XML)
    scan_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the Nessus scan was performed"
    )
    scanner_version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Nessus scanner version"
    )
    policy_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Nessus scan policy name"
    )

    # Statistics (computed from XML)
    total_hosts = models.IntegerField(
        default=0,
        help_text="Total number of hosts scanned"
    )
    total_vulnerabilities = models.IntegerField(
        default=0,
        help_text="Total number of vulnerabilities found"
    )
    scan_duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration of the scan in seconds"
    )

    # Severity breakdown
    critical_count = models.IntegerField(default=0, help_text="Critical severity vulnerabilities")
    high_count = models.IntegerField(default=0, help_text="High severity vulnerabilities")
    medium_count = models.IntegerField(default=0, help_text="Medium severity vulnerabilities")
    low_count = models.IntegerField(default=0, help_text="Low severity vulnerabilities")
    info_count = models.IntegerField(default=0, help_text="Informational findings")

    # Correlation data
    correlated_checklist_ids = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="CKL checklists correlated with this scan"
    )

    # Additional metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Custom tags for organization"
    )

    # Processing status
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('uploaded', 'Uploaded'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='uploaded',
        help_text="Current processing status of the scan"
    )

    processing_error = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if processing failed"
    )

    class Meta:
        db_table = "rmf_operations_nessus_scans"
        indexes = [
            models.Index(fields=['systemGroupId'], name='rmf_nessus_sysgrp_idx'),
            models.Index(fields=['scan_date'], name='rmf_nessus_scan_date_idx'),
            models.Index(fields=['processing_status'], name='rmf_nessus_status_idx'),
            models.Index(fields=['created_at'], name='rmf_nessus_created_idx'),
        ]
        ordering = ['-scan_date', '-created_at']

    def create_scan(
        self,
        system_group_id: uuid.UUID,
        filename: str,
        raw_xml_content: str,
        tags: Optional[List[str]] = None
    ):
        """Create a new Nessus scan record"""
        self.systemGroupId = system_group_id
        self.filename = filename
        self.raw_xml_content = raw_xml_content
        self.tags = tags if tags is not None else []
        self.processing_status = 'uploaded'

        from ..domain_events import NessusScanUploaded
        self._raise_event(NessusScanUploaded(
            aggregate_id=self.id,
            system_group_id=str(system_group_id),
            filename=filename
        ))

    def mark_processing_started(self):
        """Mark scan processing as started"""
        self.processing_status = 'processing'
        self.processing_error = None

        from ..domain_events import NessusScanProcessingStarted
        self._raise_event(NessusScanProcessingStarted(
            aggregate_id=self.id,
            filename=self.filename
        ))

    def mark_processing_completed(self, metadata: Dict[str, Any]):
        """Mark scan processing as completed with extracted metadata"""
        self.processing_status = 'completed'
        self.processing_error = None

        # Update metadata fields
        self.scan_date = metadata.get('scan_date')
        self.scanner_version = metadata.get('scanner_version')
        self.policy_name = metadata.get('policy_name')
        self.total_hosts = metadata.get('total_hosts', 0)
        self.total_vulnerabilities = metadata.get('total_vulnerabilities', 0)
        self.scan_duration_seconds = metadata.get('scan_duration_seconds')
        self.critical_count = metadata.get('critical_count', 0)
        self.high_count = metadata.get('high_count', 0)
        self.medium_count = metadata.get('medium_count', 0)
        self.low_count = metadata.get('low_count', 0)
        self.info_count = metadata.get('info_count', 0)

        from ..domain_events import NessusScanProcessingCompleted
        self._raise_event(NessusScanProcessingCompleted(
            aggregate_id=self.id,
            filename=self.filename,
            total_hosts=self.total_hosts,
            total_vulnerabilities=self.total_vulnerabilities
        ))

    def mark_processing_failed(self, error_message: str):
        """Mark scan processing as failed"""
        self.processing_status = 'failed'
        self.processing_error = error_message

        from ..domain_events import NessusScanProcessingFailed
        self._raise_event(NessusScanProcessingFailed(
            aggregate_id=self.id,
            filename=self.filename,
            error_message=error_message
        ))

    def add_correlation(self, checklist_id: uuid.UUID):
        """Add a correlated checklist"""
        if checklist_id not in self.correlated_checklist_ids:
            self.correlated_checklist_ids.append(checklist_id)

            from ..domain_events import NessusScanChecklistCorrelated
            self._raise_event(NessusScanChecklistCorrelated(
                aggregate_id=self.id,
                checklist_id=str(checklist_id)
            ))

    def remove_correlation(self, checklist_id: uuid.UUID):
        """Remove a correlated checklist"""
        if checklist_id in self.correlated_checklist_ids:
            self.correlated_checklist_ids.remove(checklist_id)

    @property
    def severity_breakdown(self) -> Dict[str, int]:
        """Get severity breakdown as dictionary"""
        return {
            'critical': self.critical_count,
            'high': self.high_count,
            'medium': self.medium_count,
            'low': self.low_count,
            'info': self.info_count
        }

    @property
    def total_severe_vulnerabilities(self) -> int:
        """Get total vulnerabilities excluding informational"""
        return self.critical_count + self.high_count + self.medium_count + self.low_count

    def __str__(self):
        return f"NessusScan({self.filename} - {self.total_hosts} hosts, {self.total_vulnerabilities} vulns)"
