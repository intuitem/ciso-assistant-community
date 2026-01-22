"""
Unit tests for StigChecklist aggregate.
"""

import uuid
import pytest
from django.utils import timezone

from ..aggregates.stig_checklist import StigChecklist


class TestStigChecklist:
    """Test StigChecklist aggregate."""

    def test_create_checklist(self):
        """Test creating a STIG checklist."""
        checklist = StigChecklist()
        system_id = uuid.uuid4()

        checklist.create_checklist(
            host_name="test-server.local",
            stig_type="Windows Server 2019",
            stig_release="Release: 2.5",
            version="1.0",
            system_group_id=system_id
        )

        assert checklist.hostName == "test-server.local"
        assert checklist.stigType == "Windows Server 2019"
        assert checklist.stigRelease == "Release: 2.5"
        assert checklist.version == "1.0"
        assert checklist.systemGroupId == system_id
        assert checklist.lifecycle_state == StigChecklist.LifecycleState.DRAFT
        assert checklist.assetInfo == {}
        assert checklist.rawCklData == {}
        assert checklist.vulnerabilityFindingIds == []
        assert checklist.tags == []
        assert not checklist.isWebDatabase

    def test_import_ckl_data(self):
        """Test importing CKL data."""
        checklist = StigChecklist()
        checklist.create_checklist("test-server", "Windows Server 2019", "Release: 2.5", "1.0")

        ckl_data = {
            "ASSET": {
                "HOST_NAME": "test-server.local",
                "HOST_IP": "192.168.1.100",
                "HOST_MAC": "00:11:22:33:44:55",
                "TECH_AREA": "Application Review",
                "WEB_OR_DATABASE": "true",
                "WEB_DB_SITE": "MyApp",
                "WEB_DB_INSTANCE": "Production"
            },
            "STIGS": {
                "iSTIG": {
                    "STIG_INFO": {
                        "SI_DATA": [
                            {"SID_NAME": "version", "SID_DATA": "1.1"},
                            {"SID_NAME": "releaseinfo", "SID_DATA": "Release: 2.6"}
                        ]
                    }
                }
            }
        }

        checklist.import_from_ckl(ckl_data)

        assert checklist.assetInfo == ckl_data["ASSET"]
        assert checklist.rawCklData == ckl_data
        assert checklist.isWebDatabase
        assert checklist.webDatabaseSite == "MyApp"
        assert checklist.webDatabaseInstance == "Production"
        assert checklist.version == "1.1"  # Updated from CKL
        assert checklist.stigRelease == "Release: 2.6"  # Updated from CKL

    def test_export_ckl_data(self):
        """Test exporting CKL data."""
        checklist = StigChecklist()
        checklist.create_checklist("test-server", "Windows Server 2019", "Release: 2.5", "1.0")

        ckl_data = {"test": "data"}
        checklist.rawCklData = ckl_data

        exported = checklist.export_to_ckl()
        assert exported == ckl_data

    def test_activate_checklist(self):
        """Test activating a checklist."""
        checklist = StigChecklist()
        checklist.create_checklist("test-server", "Windows Server 2019", "Release: 2.5", "1.0")

        checklist.activate_checklist()

        assert checklist.lifecycle_state == StigChecklist.LifecycleState.ACTIVE

    def test_archive_checklist(self):
        """Test archiving a checklist."""
        checklist = StigChecklist()
        checklist.create_checklist("test-server", "Windows Server 2019", "Release: 2.5", "1.0")
        checklist.activate_checklist()

        checklist.archive_checklist()

        assert checklist.lifecycle_state == StigChecklist.LifecycleState.ARCHIVED

    def test_add_remove_vulnerability_finding(self):
        """Test adding and removing vulnerability findings."""
        checklist = StigChecklist()
        checklist.create_checklist("test-server", "Windows Server 2019", "Release: 2.5", "1.0")

        finding_id = uuid.uuid4()
        checklist.add_vulnerability_finding(finding_id)

        assert finding_id in checklist.vulnerabilityFindingIds

        checklist.remove_vulnerability_finding(finding_id)
        assert finding_id not in checklist.vulnerabilityFindingIds

    def test_assign_to_system(self):
        """Test assigning checklist to a system."""
        checklist = StigChecklist()
        checklist.create_checklist("test-server", "Windows Server 2019", "Release: 2.5", "1.0")

        system_id = uuid.uuid4()
        checklist.assign_to_system(system_id)

        assert checklist.systemGroupId == system_id

    def test_unassign_from_system(self):
        """Test unassigning checklist from a system."""
        checklist = StigChecklist()
        checklist.create_checklist("test-server", "Windows Server 2019", "Release: 2.5", "1.0")

        system_id = uuid.uuid4()
        checklist.assign_to_system(system_id)
        assert checklist.systemGroupId == system_id

        checklist.unassign_from_system()
        assert checklist.systemGroupId is None

    def test_asset_info_methods(self):
        """Test asset information access methods."""
        checklist = StigChecklist()
        checklist.create_checklist("test-server", "Windows Server 2019", "Release: 2.5", "1.0")

        checklist.assetInfo = {
            "HOST_NAME": "test-server.local",
            "HOST_IP": "192.168.1.100,192.168.1.101",
            "HOST_MAC": "00:11:22:33:44:55,66:77:88:99:AA:BB"
        }

        assert checklist.get_asset_hostname() == "test-server.local"
        assert checklist.get_asset_ip_addresses() == ["192.168.1.100", "192.168.1.101"]
        assert checklist.get_asset_mac_addresses() == ["00:11:22:33:44:55", "66:77:88:99:AA:BB"]

    def test_lifecycle_state_checks(self):
        """Test lifecycle state checking methods."""
        checklist = StigChecklist()
        checklist.create_checklist("test-server", "Windows Server 2019", "Release: 2.5", "1.0")

        assert not checklist.is_active()
        assert checklist.can_be_activated()
        assert not checklist.can_be_archived()

        checklist.activate_checklist()

        assert checklist.is_active()
        assert not checklist.can_be_activated()
        assert checklist.can_be_archived()

    def test_system_assignment_checks(self):
        """Test system assignment checking methods."""
        checklist = StigChecklist()
        checklist.create_checklist("test-server", "Windows Server 2019", "Release: 2.5", "1.0")

        assert not checklist.has_system_assignment()

        system_id = uuid.uuid4()
        checklist.assign_to_system(system_id)

        assert checklist.has_system_assignment()

    def test_str_representation(self):
        """Test string representation."""
        checklist = StigChecklist()
        checklist.create_checklist("test-server", "Windows Server 2019", "Release: 2.5", "1.0")

        expected = f"StigChecklist({checklist.id}): test-server - Windows Server 2019"
        assert str(checklist) == expected
