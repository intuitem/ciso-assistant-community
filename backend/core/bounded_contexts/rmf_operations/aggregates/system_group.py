"""
SystemGroup Aggregate

Represents a system package (group of checklists/assets) in RMF operations.
"""

import uuid
from typing import Optional, List
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField


class SystemGroup(AggregateRoot):
    """
    System Group aggregate.

    Represents a system package that groups multiple checklists and assets
    for RMF operations. Provides system-level scoring and compliance rollup.
    """

    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    # Identity and core fields
    name = models.CharField(max_length=255, db_index=True, help_text="System name")
    description = models.TextField(blank=True, null=True, help_text="System description")

    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True,
        help_text="Current lifecycle state"
    )

    # Embedded ID arrays for relationships
    checklistIds = EmbeddedIdArrayField(
        help_text="Array of STIG checklist IDs in this system"
    )
    assetIds = EmbeddedIdArrayField(
        help_text="Array of asset IDs in this system"
    )
    nessusScanIds = EmbeddedIdArrayField(
        help_text="Array of Nessus scan IDs for this system"
    )

    # Asset hierarchy and relationships
    asset_hierarchy = models.JSONField(
        default=dict,
        blank=True,
        help_text="Asset hierarchy and relationships within this system group"
    )

    # Compliance tracking
    last_compliance_check = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last compliance verification"
    )

    # Metadata
    tags = models.JSONField(default=list, blank=True, help_text="System tags")

    # Computed fields (updated by projection handlers)
    totalChecklists = models.IntegerField(default=0, help_text="Total number of checklists")
    totalOpenVulnerabilities = models.IntegerField(default=0, help_text="Total open vulnerabilities across all checklists")
    totalCat1Open = models.IntegerField(default=0, help_text="Total CAT I open vulnerabilities")
    totalCat2Open = models.IntegerField(default=0, help_text="Total CAT II open vulnerabilities")
    totalCat3Open = models.IntegerField(default=0, help_text="Total CAT III open vulnerabilities")

    class Meta:
        db_table = 'rmf_system_groups'
        verbose_name = 'System Group'
        verbose_name_plural = 'System Groups'
        ordering = ['name']
        indexes = [
            models.Index(fields=['lifecycle_state', 'name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return f"SystemGroup({self.id}): {self.name}"

    # Business methods
    def create_system(self, name: str, description: Optional[str] = None) -> None:
        """Create a new system group"""
        self.name = name
        self.description = description
        self.lifecycle_state = self.LifecycleState.DRAFT
        self.checklistIds = []
        self.assetIds = []
        self.nessusScanIds = []
        self.tags = []

        from ..domain_events import SystemGroupCreated
        self._raise_event(SystemGroupCreated(
            aggregate_id=self.id,
            name=name,
            description=description
        ))

    def activate_system(self) -> None:
        """Activate the system group"""
        if self.lifecycle_state == self.LifecycleState.DRAFT:
            self.lifecycle_state = self.LifecycleState.ACTIVE

            from ..domain_events import SystemGroupActivated
            self._raise_event(SystemGroupActivated(
                aggregate_id=self.id,
                name=self.name
            ))

    def archive_system(self) -> None:
        """Archive the system group"""
        if self.lifecycle_state == self.LifecycleState.ACTIVE:
            self.lifecycle_state = self.LifecycleState.ARCHIVED

            from ..domain_events import SystemGroupArchived
            self._raise_event(SystemGroupArchived(
                aggregate_id=self.id,
                name=self.name
            ))

    def mark_compliance_checked(self) -> None:
        """Mark that compliance has been verified for this system"""
        from django.utils import timezone
        self.last_compliance_check = timezone.now()

        from ..domain_events import SystemGroupComplianceChecked
        self._raise_event(SystemGroupComplianceChecked(
            aggregate_id=self.id,
            system_name=self.name,
            checked_at=self.last_compliance_check
        ))

    def add_checklist(self, checklist_id: uuid.UUID) -> None:
        """Add a checklist to the system"""
        if checklist_id not in self.checklistIds:
            self.checklistIds.append(checklist_id)

            from ..domain_events import ChecklistAddedToSystem
            self._raise_event(ChecklistAddedToSystem(
                aggregate_id=self.id,
                system_name=self.name,
                checklist_id=str(checklist_id)
            ))

    def remove_checklist(self, checklist_id: uuid.UUID) -> None:
        """Remove a checklist from the system"""
        if checklist_id in self.checklistIds:
            self.checklistIds.remove(checklist_id)

    def add_asset(self, asset_id: uuid.UUID) -> None:
        """Add an asset to the system"""
        if asset_id not in self.assetIds:
            self.assetIds.append(asset_id)

            from ..domain_events import AssetAddedToSystem
            self._raise_event(AssetAddedToSystem(
                aggregate_id=self.id,
                system_name=self.name,
                asset_id=str(asset_id)
            ))

    def remove_asset(self, asset_id: uuid.UUID) -> None:
        """Remove an asset from the system"""
        if asset_id in self.assetIds:
            self.assetIds.remove(asset_id)

    def add_nessus_scan(self, scan_id: uuid.UUID) -> None:
        """Add a Nessus scan to the system"""
        if scan_id not in self.nessusScanIds:
            self.nessusScanIds.append(scan_id)

    def remove_nessus_scan(self, scan_id: uuid.UUID) -> None:
        """Remove a Nessus scan from the system"""
        if scan_id in self.nessusScanIds:
            self.nessusScanIds.remove(scan_id)

    def update_compliance_stats(self, total_checklists: int = None,
                               total_open: int = None, cat1_open: int = None,
                               cat2_open: int = None, cat3_open: int = None) -> None:
        """Update computed compliance statistics"""
        if total_checklists is not None:
            self.totalChecklists = total_checklists
        if total_open is not None:
            self.totalOpenVulnerabilities = total_open
        if cat1_open is not None:
            self.totalCat1Open = cat1_open
        if cat2_open is not None:
            self.totalCat2Open = cat2_open
        if cat3_open is not None:
            self.totalCat3Open = cat3_open

    # Query methods
    def get_active_checklists(self) -> List[uuid.UUID]:
        """Get list of active checklist IDs"""
        return self.checklistIds.copy()

    def get_assigned_assets(self) -> List[uuid.UUID]:
        """Get list of assigned asset IDs"""
        return self.assetIds.copy()

    def is_active(self) -> bool:
        """Check if system is active"""
        return self.lifecycle_state == self.LifecycleState.ACTIVE

    def can_be_activated(self) -> bool:
        """Check if system can be activated"""
        return self.lifecycle_state == self.LifecycleState.DRAFT

    def can_be_archived(self) -> bool:
        """Check if system can be archived"""
        return self.lifecycle_state == self.LifecycleState.ACTIVE
