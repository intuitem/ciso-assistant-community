"""
StigChecklist Aggregate

Represents a STIG checklist (CKL file) with vulnerability findings.
"""

import uuid
from typing import Optional, Dict, Any, List
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField


class StigChecklist(AggregateRoot):
    """
    STIG Checklist aggregate.

    Represents a STIG checklist (CKL file) containing vulnerability findings
    and asset information extracted from SCAP tools.
    """

    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    # Identity and system relationship
    systemGroupId = models.UUIDField(
        db_index=True,
        null=True,
        blank=True,
        help_text="ID of the system group this checklist belongs to"
    )
    hostName = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Hostname of the asset being checked"
    )

    # STIG metadata
    stigType = models.CharField(
        max_length=255,
        db_index=True,
        help_text="STIG type (e.g., 'Windows Server 2019')"
    )
    stigRelease = models.CharField(
        max_length=255,
        help_text="STIG release info (e.g., 'Release: 2.5')"
    )
    version = models.CharField(
        max_length=50,
        help_text="STIG version number"
    )

    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True,
        help_text="Current lifecycle state"
    )

    # Asset information (extracted from CKL file)
    assetInfo = models.JSONField(
        default=dict,
        blank=True,
        help_text="Asset information from CKL file (HOST_NAME, HOST_IP, etc.)"
    )

    # Raw CKL data for export/re-import
    rawCklData = models.JSONField(
        default=dict,
        blank=True,
        help_text="Complete CKL file structure for export"
    )

    # Web/Database specific fields (OpenRMF naming convention)
    isWebDatabase = models.BooleanField(
        default=False,
        help_text="Whether this is a web/database STIG"
    )
    webDatabaseSite = models.CharField(
        max_length=255,
        blank=True,
        help_text="Web site/application name"
    )
    webDatabaseInstance = models.CharField(
        max_length=255,
        blank=True,
        help_text="Database instance name"
    )

    # Asset type classification
    ASSET_TYPES = [
        ('computing', 'Computing'),
        ('network', 'Network'),
        ('storage', 'Storage'),
        ('application', 'Application'),
        ('database', 'Database'),
        ('web_server', 'Web Server'),
        ('other', 'Other'),
    ]

    asset_type = models.CharField(
        max_length=20,
        choices=ASSET_TYPES,
        default='computing',
        help_text="Type of asset this checklist applies to"
    )

    # Relationships
    vulnerabilityFindingIds = EmbeddedIdArrayField(
        help_text="Array of vulnerability finding IDs in this checklist"
    )

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Checklist tags"
    )

    class Meta:
        db_table = 'rmf_stig_checklists'
        verbose_name = 'STIG Checklist'
        verbose_name_plural = 'STIG Checklists'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['systemGroupId', 'lifecycle_state']),
            models.Index(fields=['stigType', 'version']),
            models.Index(fields=['hostName']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]
        # Ensure unique hostname per system group (optional constraint)
        # unique_together = [['systemGroupId', 'hostName']]

    def __str__(self):
        return f"StigChecklist({self.id}): {self.hostName} - {self.stigType}"

    # Business methods
    def create_checklist(self, host_name: str, stig_type: str,
                        stig_release: str, version: str,
                        system_group_id: Optional[uuid.UUID] = None) -> None:
        """Create a new STIG checklist"""
        self.hostName = host_name
        self.stigType = stig_type
        self.stigRelease = stig_release
        self.version = version
        self.systemGroupId = system_group_id
        self.lifecycle_state = self.LifecycleState.DRAFT
        self.assetInfo = {}
        self.rawCklData = {}
        self.vulnerabilityFindingIds = []
        self.tags = []
        self.isWebDatabase = False

        from ..domain_events import StigChecklistCreated
        self._raise_event(StigChecklistCreated(
            aggregate_id=self.id,
            host_name=host_name,
            stig_type=stig_type,
            system_group_id=str(system_group_id) if system_group_id else None
        ))

    def import_from_ckl(self, ckl_data: Dict[str, Any]) -> None:
        """Import checklist data from parsed CKL file"""
        # Update asset information
        if 'ASSET' in ckl_data:
            self.assetInfo = ckl_data['ASSET']

            # Extract hostname if not set
            if not self.hostName and 'HOST_NAME' in ckl_data['ASSET']:
                self.hostName = ckl_data['ASSET']['HOST_NAME']

            # Check for web/database flags
            if 'WEB_OR_DATABASE' in ckl_data['ASSET']:
                self.isWebDatabase = ckl_data['ASSET']['WEB_OR_DATABASE'].lower() == 'true'

            if 'WEB_DB_SITE' in ckl_data['ASSET']:
                self.webDatabaseSite = ckl_data['ASSET']['WEB_DB_SITE']

            if 'WEB_DB_INSTANCE' in ckl_data['ASSET']:
                self.webDatabaseInstance = ckl_data['ASSET']['WEB_DB_INSTANCE']

        # Store raw CKL data for export
        self.rawCklData = ckl_data

        # Update STIG metadata if available
        if 'STIGS' in ckl_data and 'iSTIG' in ckl_data['STIGS']:
            stig_info = ckl_data['STIGS']['iSTIG']
            if 'STIG_INFO' in stig_info and 'SI_DATA' in stig_info['STIG_INFO']:
                si_data = stig_info['STIG_INFO']['SI_DATA']
                # Extract STIG metadata from SI_DATA array
                for item in si_data:
                    if item.get('SID_NAME') == 'version':
                        self.version = item.get('SID_DATA', self.version)
                    elif item.get('SID_NAME') == 'releaseinfo':
                        self.stigRelease = item.get('SID_DATA', self.stigRelease)

        from ..domain_events import StigChecklistImported
        self._raise_event(StigChecklistImported(
            aggregate_id=self.id,
            host_name=self.hostName,
            stig_type=self.stigType
        ))

    def export_to_ckl(self) -> Dict[str, Any]:
        """Export checklist data as CKL-compatible structure"""
        return self.rawCklData.copy()

    def activate_checklist(self) -> None:
        """Activate the checklist"""
        if self.lifecycle_state == self.LifecycleState.DRAFT:
            self.lifecycle_state = self.LifecycleState.ACTIVE

            from ..domain_events import StigChecklistActivated
            self._raise_event(StigChecklistActivated(
                aggregate_id=self.id,
                host_name=self.hostName,
                stig_type=self.stigType
            ))

    def archive_checklist(self) -> None:
        """Archive the checklist"""
        if self.lifecycle_state == self.LifecycleState.ACTIVE:
            self.lifecycle_state = self.LifecycleState.ARCHIVED

    def add_vulnerability_finding(self, finding_id: uuid.UUID) -> None:
        """Add a vulnerability finding to this checklist"""
        if finding_id not in self.vulnerabilityFindingIds:
            self.vulnerabilityFindingIds.append(finding_id)

    def remove_vulnerability_finding(self, finding_id: uuid.UUID) -> None:
        """Remove a vulnerability finding from this checklist"""
        if finding_id in self.vulnerabilityFindingIds:
            self.vulnerabilityFindingIds.remove(finding_id)

    def assign_to_system(self, system_group_id: uuid.UUID) -> None:
        """Assign checklist to a system group"""
        if self.systemGroupId != system_group_id:
            self.systemGroupId = system_group_id

    def unassign_from_system(self) -> None:
        """Remove checklist from its system group"""
        self.systemGroupId = None

    # Query methods
    def get_vulnerability_findings(self) -> List[uuid.UUID]:
        """Get list of vulnerability finding IDs"""
        return self.vulnerabilityFindingIds.copy()

    def get_asset_hostname(self) -> str:
        """Get hostname from asset info or field"""
        return self.assetInfo.get('HOST_NAME', self.hostName)

    def get_asset_ip_addresses(self) -> List[str]:
        """Get IP addresses from asset info"""
        ip_str = self.assetInfo.get('HOST_IP', '')
        return [ip.strip() for ip in ip_str.split(',') if ip.strip()]

    def get_asset_mac_addresses(self) -> List[str]:
        """Get MAC addresses from asset info"""
        mac_str = self.assetInfo.get('HOST_MAC', '')
        return [mac.strip() for mac in mac_str.split(',') if mac.strip()]

    def is_active(self) -> bool:
        """Check if checklist is active"""
        return self.lifecycle_state == self.LifecycleState.ACTIVE

    def has_system_assignment(self) -> bool:
        """Check if checklist is assigned to a system"""
        return self.systemGroupId is not None

    def can_be_activated(self) -> bool:
        """Check if checklist can be activated"""
        return (self.lifecycle_state == self.LifecycleState.DRAFT and
                self.rawCklData)  # Must have imported data

    def can_be_archived(self) -> bool:
        """Check if checklist can be archived"""
        return self.lifecycle_state == self.LifecycleState.ACTIVE
