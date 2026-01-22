"""
Unit tests for RMF Operations repositories.
"""

import uuid
import pytest
from django.test import TestCase

from ..aggregates.system_group import SystemGroup
from ..aggregates.stig_checklist import StigChecklist
from ..aggregates.vulnerability_finding import VulnerabilityFinding
from ..aggregates.checklist_score import ChecklistScore
from ..repositories.system_group_repository import SystemGroupRepository
from ..repositories.stig_checklist_repository import StigChecklistRepository
from ..repositories.vulnerability_finding_repository import VulnerabilityFindingRepository
from ..repositories.checklist_score_repository import ChecklistScoreRepository


class TestSystemGroupRepository(TestCase):
    """Test SystemGroupRepository."""

    def setUp(self):
        self.repo = SystemGroupRepository()

    def test_save_and_retrieve(self):
        """Test saving and retrieving a system group."""
        system = SystemGroup()
        system.create_system("Test System", "Test description")

        self.repo.save(system)

        retrieved = self.repo.get_by_id(system.id)
        assert retrieved is not None
        assert retrieved.name == "Test System"
        assert retrieved.description == "Test description"

    def test_find_by_name(self):
        """Test finding system by name."""
        system = SystemGroup()
        system.create_system("Unique System Name")

        self.repo.save(system)

        found = self.repo.find_by_name("Unique System Name")
        assert found is not None
        assert found.id == system.id

        not_found = self.repo.find_by_name("Nonexistent System")
        assert not_found is None

    def test_find_active_systems(self):
        """Test finding active systems."""
        # Create draft system
        draft_system = SystemGroup()
        draft_system.create_system("Draft System")
        self.repo.save(draft_system)

        # Create active system
        active_system = SystemGroup()
        active_system.create_system("Active System")
        active_system.activate_system()
        self.repo.save(active_system)

        active_systems = self.repo.find_active_systems()
        assert len(active_systems) == 1
        assert active_systems[0].id == active_system.id

    def test_find_systems_with_checklists(self):
        """Test finding systems with checklists."""
        # Create system without checklists
        empty_system = SystemGroup()
        empty_system.create_system("Empty System")
        self.repo.save(empty_system)

        # Create system with checklist
        system_with_checklist = SystemGroup()
        system_with_checklist.create_system("System with Checklist")
        checklist_id = uuid.uuid4()
        system_with_checklist.add_checklist(checklist_id)
        self.repo.save(system_with_checklist)

        systems_with_checklists = self.repo.find_systems_with_checklists()
        assert len(systems_with_checklists) == 1
        assert systems_with_checklists[0].id == system_with_checklist.id


class TestStigChecklistRepository(TestCase):
    """Test StigChecklistRepository."""

    def setUp(self):
        self.repo = StigChecklistRepository()

    def test_save_and_retrieve(self):
        """Test saving and retrieving a checklist."""
        checklist = StigChecklist()
        checklist.create_checklist(
            host_name="test-server.local",
            stig_type="Windows Server 2019",
            stig_release="Release: 2.5",
            version="1.0"
        )

        self.repo.save(checklist)

        retrieved = self.repo.get_by_id(checklist.id)
        assert retrieved is not None
        assert retrieved.hostName == "test-server.local"
        assert retrieved.stigType == "Windows Server 2019"

    def test_find_by_hostname_and_stig(self):
        """Test finding checklist by hostname and STIG type."""
        checklist = StigChecklist()
        checklist.create_checklist(
            host_name="unique-server.local",
            stig_type="Windows Server 2019",
            stig_release="Release: 2.5",
            version="1.0"
        )

        self.repo.save(checklist)

        found = self.repo.find_by_hostname_and_stig("unique-server.local", "Windows Server 2019")
        assert found is not None
        assert found.id == checklist.id

        not_found = self.repo.find_by_hostname_and_stig("unique-server.local", "Linux")
        assert not_found is None

    def test_find_by_system_group(self):
        """Test finding checklists by system group."""
        system_id = uuid.uuid4()

        # Create checklist in system
        checklist_in_system = StigChecklist()
        checklist_in_system.create_checklist(
            host_name="server1.local",
            stig_type="Windows Server 2019",
            stig_release="Release: 2.5",
            version="1.0",
            system_group_id=system_id
        )
        self.repo.save(checklist_in_system)

        # Create checklist not in system
        checklist_outside = StigChecklist()
        checklist_outside.create_checklist(
            host_name="server2.local",
            stig_type="Windows Server 2019",
            stig_release="Release: 2.5",
            version="1.0"
        )
        self.repo.save(checklist_outside)

        system_checklists = self.repo.find_by_system_group(system_id)
        assert len(system_checklists) == 1
        assert system_checklists[0].id == checklist_in_system.id

    def test_assign_to_system(self):
        """Test assigning checklist to system."""
        checklist = StigChecklist()
        checklist.create_checklist(
            host_name="test-server.local",
            stig_type="Windows Server 2019",
            stig_release="Release: 2.5",
            version="1.0"
        )
        self.repo.save(checklist)

        system_id = uuid.uuid4()
        user_id = uuid.uuid4()
        username = "test_user"
        success = self.repo.assign_to_system(
            checklist_id=checklist.id,
            system_group_id=system_id,
            user_id=user_id,
            username=username
        )

        assert success
        updated_checklist = self.repo.get_by_id(checklist.id)
        assert updated_checklist.systemGroupId == system_id


class TestVulnerabilityFindingRepository(TestCase):
    """Test VulnerabilityFindingRepository."""

    def setUp(self):
        self.repo = VulnerabilityFindingRepository()

    def test_save_and_retrieve(self):
        """Test saving and retrieving a finding."""
        finding = VulnerabilityFinding()
        checklist_id = uuid.uuid4()

        finding.create_finding(
            checklist_id=checklist_id,
            vuln_id="V-12345",
            stig_id="Windows_2019_STIG",
            rule_id="SV-12345r1_rule",
            rule_title="Test Rule",
            severity_category="cat1"
        )

        self.repo.save(finding)

        retrieved = self.repo.get_by_id(finding.id)
        assert retrieved is not None
        assert retrieved.vulnId == "V-12345"
        assert retrieved.ruleTitle == "Test Rule"

    def test_find_by_checklist(self):
        """Test finding findings by checklist."""
        checklist_id = uuid.uuid4()

        finding1 = VulnerabilityFinding()
        finding1.create_finding(
            checklist_id=checklist_id,
            vuln_id="V-12345",
            stig_id="Windows_2019_STIG",
            rule_id="SV-12345r1_rule",
            rule_title="Rule 1",
            severity_category="cat1"
        )
        self.repo.save(finding1)

        finding2 = VulnerabilityFinding()
        finding2.create_finding(
            checklist_id=checklist_id,
            vuln_id="V-12346",
            stig_id="Windows_2019_STIG",
            rule_id="SV-12346r1_rule",
            rule_title="Rule 2",
            severity_category="cat2"
        )
        self.repo.save(finding2)

        # Create finding in different checklist
        other_checklist_id = uuid.uuid4()
        finding3 = VulnerabilityFinding()
        finding3.create_finding(
            checklist_id=other_checklist_id,
            vuln_id="V-12347",
            stig_id="Windows_2019_STIG",
            rule_id="SV-12347r1_rule",
            rule_title="Rule 3",
            severity_category="cat1"
        )
        self.repo.save(finding3)

        checklist_findings = self.repo.find_by_checklist(checklist_id)
        assert len(checklist_findings) == 2
        vuln_ids = {f.vulnId for f in checklist_findings}
        assert vuln_ids == {"V-12345", "V-12346"}

    def test_find_open_findings(self):
        """Test finding open findings."""
        checklist_id = uuid.uuid4()

        # Create open finding
        open_finding = VulnerabilityFinding()
        open_finding.create_finding(
            checklist_id=checklist_id,
            vuln_id="V-12345",
            stig_id="Windows_2019_STIG",
            rule_id="SV-12345r1_rule",
            rule_title="Open Rule",
            severity_category="cat1"
        )
        open_finding.update_status("open")
        self.repo.save(open_finding)

        # Create closed finding
        closed_finding = VulnerabilityFinding()
        closed_finding.create_finding(
            checklist_id=checklist_id,
            vuln_id="V-12346",
            stig_id="Windows_2019_STIG",
            rule_id="SV-12346r1_rule",
            rule_title="Closed Rule",
            severity_category="cat1"
        )
        closed_finding.update_status("not_a_finding")
        self.repo.save(closed_finding)

        open_findings = self.repo.find_open_findings()
        assert len(open_findings) == 1
        assert open_findings[0].vulnId == "V-12345"

    def test_count_findings_by_status(self):
        """Test counting findings by status."""
        checklist_id = uuid.uuid4()

        # Create findings with different statuses
        for vuln_id, status in [("V-1", "open"), ("V-2", "not_a_finding"), ("V-3", "not_applicable"), ("V-4", "not_reviewed")]:
            finding = VulnerabilityFinding()
            finding.create_finding(
                checklist_id=checklist_id,
                vuln_id=vuln_id,
                stig_id="Windows_2019_STIG",
                rule_id=f"SV-{vuln_id}r1_rule",
                rule_title=f"Rule {vuln_id}",
                severity_category="cat1"
            )
            finding.update_status(status)
            self.repo.save(finding)

        counts = self.repo.count_findings_by_status(checklist_id)

        assert counts["open"] == 1
        assert counts["not_a_finding"] == 1
        assert counts["not_applicable"] == 1
        assert counts["not_reviewed"] == 1


class TestChecklistScoreRepository(TestCase):
    """Test ChecklistScoreRepository."""

    def setUp(self):
        self.repo = ChecklistScoreRepository()

    def test_save_and_retrieve(self):
        """Test saving and retrieving a score."""
        score = ChecklistScore()
        checklist_id = uuid.uuid4()

        score.create_score(
            checklist_id=checklist_id,
            system_group_id=None,
            host_name="test-server.local",
            stig_type="Windows Server 2019"
        )

        self.repo.save(score)

        retrieved = self.repo.find_by_checklist(checklist_id)
        assert retrieved is not None
        assert retrieved.hostName == "test-server.local"
        assert retrieved.stigType == "Windows Server 2019"

    def test_find_by_checklist(self):
        """Test finding score by checklist ID."""
        checklist_id = uuid.uuid4()
        score = ChecklistScore()

        score.create_score(
            checklist_id=checklist_id,
            system_group_id=None,
            host_name="test-server.local",
            stig_type="Windows Server 2019"
        )

        self.repo.save(score)

        found = self.repo.find_by_checklist(checklist_id)
        assert found is not None
        assert found.id == score.id

        not_found = self.repo.find_by_checklist(uuid.uuid4())
        assert not_found is None

    def test_update_score_from_findings(self):
        """Test updating score from findings data."""
        checklist_id = uuid.uuid4()
        score = ChecklistScore()

        score.create_score(
            checklist_id=checklist_id,
            system_group_id=None,
            host_name="test-server.local",
            stig_type="Windows Server 2019"
        )
        self.repo.save(score)

        findings_data = {
            'cat1': {'open': 2, 'not_a_finding': 1, 'not_applicable': 0, 'not_reviewed': 0},
            'cat2': {'open': 1, 'not_a_finding': 2, 'not_applicable': 0, 'not_reviewed': 0},
            'cat3': {'open': 0, 'not_a_finding': 1, 'not_applicable': 1, 'not_reviewed': 0}
        }

        success = self.repo.update_score_from_findings(checklist_id, findings_data)
        assert success

        updated_score = self.repo.find_by_checklist(checklist_id)
        assert updated_score.totalCat1Open == 2
        assert updated_score.totalCat2NotAFinding == 2
        assert updated_score.totalOpen == 3  # 2 + 1 + 0
        assert updated_score.totalNotAFinding == 4  # 1 + 2 + 1


class TestRepositoryFieldNameFixes(TestCase):
    """
    Tests to verify bug fixes for field name mismatches between
    aggregates (camelCase) and repository code.

    These tests ensure that:
    - SystemGroup.name is used instead of non-existent .title
    - StigChecklist uses hostName, stigType instead of snake_case variants
    - Import/export methods use correct field names
    """

    def test_system_group_uses_name_field(self):
        """Verify SystemGroup repository uses .name not .title"""
        repo = SystemGroupRepository()
        system = SystemGroup()
        system.create_system("Test System Name", "Description")
        repo.save(system)

        # Verify we can access the name field
        retrieved = repo.get_by_id(system.id)
        assert retrieved.name == "Test System Name"
        # Verify there's no title attribute
        assert not hasattr(retrieved, 'title') or getattr(retrieved, 'title', None) is None

    def test_stig_checklist_uses_camelcase_fields(self):
        """Verify StigChecklist uses camelCase field names"""
        repo = StigChecklistRepository()
        checklist = StigChecklist()
        checklist.create_checklist(
            host_name="test-host.local",
            stig_type="Windows Server 2019",
            stig_release="Release: 2.5",
            version="1.0"
        )
        repo.save(checklist)

        retrieved = repo.get_by_id(checklist.id)
        # Verify camelCase fields exist and are correct
        assert retrieved.hostName == "test-host.local"
        assert retrieved.stigType == "Windows Server 2019"
        assert retrieved.stigRelease == "Release: 2.5"
        assert retrieved.version == "1.0"

    def test_import_ckl_uses_correct_fields(self):
        """Test that import_ckl method uses correct field names"""
        repo = StigChecklistRepository()
        checklist = StigChecklist()
        checklist.create_checklist(
            host_name="original-host.local",
            stig_type="Windows Server 2016",
            stig_release="Release: 1.0",
            version="1.0"
        )
        repo.save(checklist)

        # Import CKL data
        ckl_content = "<CHECKLIST>test content</CHECKLIST>"
        parsed_data = {
            'stig_type': 'Windows Server 2019',
            'stig_release': 'Release: 3.0',
            'stig_version': '2.0',
            'host_name': 'updated-host.local',
            'host_ip': '192.168.1.100',
            'host_fqdn': 'updated-host.local.domain.com',
            'asset_info': {
                'web_or_database': False,
                'inferred_asset_type': 'computing'
            }
        }

        user_id = uuid.uuid4()
        username = "test_user"
        success = repo.import_ckl(
            checklist_id=checklist.id,
            ckl_content=ckl_content,
            parsed_data=parsed_data,
            user_id=user_id,
            username=username
        )

        assert success

        # Verify fields were updated using correct camelCase names
        updated = repo.get_by_id(checklist.id)
        assert updated.hostName == "updated-host.local"
        assert updated.stigType == "Windows Server 2019"
        assert updated.stigRelease == "Release: 3.0"
        assert updated.version == "2.0"
        assert updated.rawCklData is not None
        assert 'raw_content' in updated.rawCklData

    def test_export_ckl_uses_correct_fields(self):
        """Test that export_ckl method uses correct field names"""
        repo = StigChecklistRepository()
        checklist = StigChecklist()
        checklist.create_checklist(
            host_name="export-test.local",
            stig_type="Windows Server 2019",
            stig_release="Release: 2.5",
            version="1.0"
        )
        # Set rawCklData directly
        checklist.rawCklData = {'raw_content': '<CHECKLIST>export test</CHECKLIST>'}
        repo.save(checklist)

        user_id = uuid.uuid4()
        username = "test_user"
        content = repo.export_ckl(
            checklist_id=checklist.id,
            user_id=user_id,
            username=username
        )

        assert content is not None
        assert '<CHECKLIST>' in content

    def test_unassign_from_system_uses_correct_fields(self):
        """Test that unassign_from_system uses correct field names"""
        repo = StigChecklistRepository()
        system_id = uuid.uuid4()

        checklist = StigChecklist()
        checklist.create_checklist(
            host_name="unassign-test.local",
            stig_type="Windows Server 2019",
            stig_release="Release: 2.5",
            version="1.0",
            system_group_id=system_id
        )
        repo.save(checklist)

        user_id = uuid.uuid4()
        username = "test_user"
        success = repo.unassign_from_system(
            checklist_id=checklist.id,
            user_id=user_id,
            username=username
        )

        assert success
        updated = repo.get_by_id(checklist.id)
        assert updated.systemGroupId is None
