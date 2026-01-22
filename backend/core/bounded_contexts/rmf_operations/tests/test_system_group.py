"""
Unit tests for SystemGroup aggregate.
"""

import uuid
import pytest
from django.utils import timezone

from ..aggregates.system_group import SystemGroup


class TestSystemGroup:
    """Test SystemGroup aggregate."""

    def test_create_system_group(self):
        """Test creating a system group."""
        system = SystemGroup()
        system.create_system(
            name="Test System",
            description="A test system group"
        )

        assert system.name == "Test System"
        assert system.description == "A test system group"
        assert system.lifecycle_state == SystemGroup.LifecycleState.DRAFT
        assert system.checklistIds == []
        assert system.assetIds == []
        assert system.nessusScanIds == []
        assert system.tags == []

    def test_activate_system(self):
        """Test activating a system."""
        system = SystemGroup()
        system.create_system("Test System")

        system.activate_system()

        assert system.lifecycle_state == SystemGroup.LifecycleState.ACTIVE

    def test_cannot_activate_non_draft_system(self):
        """Test that only draft systems can be activated."""
        system = SystemGroup()
        system.create_system("Test System")
        system.lifecycle_state = SystemGroup.LifecycleState.ACTIVE

        # Should not change state
        system.activate_system()
        assert system.lifecycle_state == SystemGroup.LifecycleState.ACTIVE

    def test_archive_system(self):
        """Test archiving a system."""
        system = SystemGroup()
        system.create_system("Test System")
        system.activate_system()

        system.archive_system()

        assert system.lifecycle_state == SystemGroup.LifecycleState.ARCHIVED

    def test_cannot_archive_non_active_system(self):
        """Test that only active systems can be archived."""
        system = SystemGroup()
        system.create_system("Test System")

        # Should not change state
        system.archive_system()
        assert system.lifecycle_state == SystemGroup.LifecycleState.DRAFT

    def test_add_checklist(self):
        """Test adding a checklist to a system."""
        system = SystemGroup()
        system.create_system("Test System")

        checklist_id = uuid.uuid4()
        system.add_checklist(checklist_id)

        assert checklist_id in system.checklistIds

    def test_remove_checklist(self):
        """Test removing a checklist from a system."""
        system = SystemGroup()
        system.create_system("Test System")

        checklist_id = uuid.uuid4()
        system.add_checklist(checklist_id)
        assert checklist_id in system.checklistIds

        system.remove_checklist(checklist_id)
        assert checklist_id not in system.checklistIds

    def test_add_asset(self):
        """Test adding an asset to a system."""
        system = SystemGroup()
        system.create_system("Test System")

        asset_id = uuid.uuid4()
        system.add_asset(asset_id)

        assert asset_id in system.assetIds

    def test_remove_asset(self):
        """Test removing an asset from a system."""
        system = SystemGroup()
        system.create_system("Test System")

        asset_id = uuid.uuid4()
        system.add_asset(asset_id)
        assert asset_id in system.assetIds

        system.remove_asset(asset_id)
        assert asset_id not in system.assetIds

    def test_add_nessus_scan(self):
        """Test adding a Nessus scan to a system."""
        system = SystemGroup()
        system.create_system("Test System")

        scan_id = uuid.uuid4()
        system.add_nessus_scan(scan_id)

        assert scan_id in system.nessusScanIds

    def test_remove_nessus_scan(self):
        """Test removing a Nessus scan from a system."""
        system = SystemGroup()
        system.create_system("Test System")

        scan_id = uuid.uuid4()
        system.add_nessus_scan(scan_id)
        assert scan_id in system.nessusScanIds

        system.remove_nessus_scan(scan_id)
        assert scan_id not in system.nessusScanIds

    def test_update_compliance_stats(self):
        """Test updating compliance statistics."""
        system = SystemGroup()
        system.create_system("Test System")

        system.update_compliance_stats(
            total_checklists=5,
            total_open=10,
            cat1_open=2,
            cat2_open=3,
            cat3_open=5
        )

        assert system.totalChecklists == 5
        assert system.totalOpenVulnerabilities == 10
        assert system.totalCat1Open == 2
        assert system.totalCat2Open == 3
        assert system.totalCat3Open == 5

    def test_query_methods(self):
        """Test query methods."""
        system = SystemGroup()
        system.create_system("Test System")

        checklist_id = uuid.uuid4()
        asset_id = uuid.uuid4()
        system.add_checklist(checklist_id)
        system.add_asset(asset_id)

        assert system.get_active_checklists() == [checklist_id]
        assert system.get_assigned_assets() == [asset_id]

    def test_lifecycle_state_checks(self):
        """Test lifecycle state checking methods."""
        system = SystemGroup()
        system.create_system("Test System")

        assert not system.is_active()
        assert system.can_be_activated()
        assert not system.can_be_archived()

        system.activate_system()

        assert system.is_active()
        assert not system.can_be_activated()
        assert system.can_be_archived()

    def test_str_representation(self):
        """Test string representation."""
        system = SystemGroup()
        system.create_system("Test System")

        expected = f"SystemGroup({system.id}): Test System"
        assert str(system) == expected
