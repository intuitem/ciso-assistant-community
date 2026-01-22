"""
Unit tests for ChecklistScore aggregate.
"""

import uuid
import pytest
from django.utils import timezone

from ..aggregates.checklist_score import ChecklistScore


class TestChecklistScore:
    """Test ChecklistScore aggregate."""

    def test_create_score(self):
        """Test creating a checklist score."""
        score = ChecklistScore()
        checklist_id = uuid.uuid4()
        system_id = uuid.uuid4()

        score.create_score(
            checklist_id=checklist_id,
            system_group_id=system_id,
            host_name="test-server.local",
            stig_type="Windows Server 2019"
        )

        assert score.checklistId == checklist_id
        assert score.systemGroupId == system_id
        assert score.hostName == "test-server.local"
        assert score.stigType == "Windows Server 2019"

        # All counts should be zero initially
        assert score.totalCat1Open == 0
        assert score.totalCat1NotAFinding == 0
        assert score.totalCat1NotApplicable == 0
        assert score.totalCat1NotReviewed == 0

    def test_reset_counts(self):
        """Test resetting counts."""
        score = ChecklistScore()
        checklist_id = uuid.uuid4()

        score.create_score(checklist_id, None, "test-server", "Windows Server 2019")

        # Set some counts
        score.totalCat1Open = 5
        score.totalCat2NotAFinding = 3
        score.totalCat3NotReviewed = 2

        score.reset_counts()

        assert score.totalCat1Open == 0
        assert score.totalCat2NotAFinding == 0
        assert score.totalCat3NotReviewed == 0

    def test_update_from_findings(self):
        """Test updating counts from findings data."""
        score = ChecklistScore()
        checklist_id = uuid.uuid4()

        score.create_score(checklist_id, None, "test-server", "Windows Server 2019")

        findings_data = {
            'cat1': {
                'open': 2,
                'not_a_finding': 3,
                'not_applicable': 1,
                'not_reviewed': 0
            },
            'cat2': {
                'open': 1,
                'not_a_finding': 2,
                'not_applicable': 0,
                'not_reviewed': 1
            },
            'cat3': {
                'open': 0,
                'not_a_finding': 1,
                'not_applicable': 0,
                'not_reviewed': 2
            }
        }

        score.update_from_findings(findings_data)

        # Check CAT 1
        assert score.totalCat1Open == 2
        assert score.totalCat1NotAFinding == 3
        assert score.totalCat1NotApplicable == 1
        assert score.totalCat1NotReviewed == 0

        # Check CAT 2
        assert score.totalCat2Open == 1
        assert score.totalCat2NotAFinding == 2
        assert score.totalCat2NotApplicable == 0
        assert score.totalCat2NotReviewed == 1

        # Check CAT 3
        assert score.totalCat3Open == 0
        assert score.totalCat3NotAFinding == 1
        assert score.totalCat3NotApplicable == 0
        assert score.totalCat3NotReviewed == 2

    def test_computed_properties(self):
        """Test computed properties."""
        score = ChecklistScore()
        checklist_id = uuid.uuid4()

        score.create_score(checklist_id, None, "test-server", "Windows Server 2019")

        # Set up some test data
        score.totalCat1Open = 2
        score.totalCat1NotAFinding = 3
        score.totalCat2Open = 1
        score.totalCat2NotAFinding = 2
        score.totalCat3Open = 0
        score.totalCat3NotAFinding = 1

        # Test totals
        assert score.totalOpen == 3  # 2 + 1 + 0
        assert score.totalNotAFinding == 6  # 3 + 2 + 1
        assert score.totalNotApplicable == 0
        assert score.totalNotReviewed == 0

        # Test category totals
        assert score.totalCat1 == 5  # 2 + 3 + 0 + 0
        assert score.totalCat2 == 3  # 1 + 2 + 0 + 0
        assert score.totalCat3 == 1  # 0 + 1 + 0 + 0

        # Test total vulnerabilities
        assert score.totalVulnerabilities == 9  # 5 + 3 + 1

    def test_compliance_percentage(self):
        """Test compliance percentage calculation."""
        score = ChecklistScore()
        checklist_id = uuid.uuid4()

        score.create_score(checklist_id, None, "test-server", "Windows Server 2019")

        # All closed (compliant)
        score.totalCat1NotAFinding = 5
        score.totalCat2NotAFinding = 3
        score.totalCat3NotAFinding = 1
        assert score.get_compliance_percentage() == 100.0

        # All open (not compliant)
        score.reset_counts()
        score.totalCat1Open = 5
        assert score.get_compliance_percentage() == 0.0

        # Mixed (50% compliant)
        score.reset_counts()
        score.totalCat1NotAFinding = 3
        score.totalCat1Open = 3
        assert score.get_compliance_percentage() == 50.0

        # Empty checklist
        score.reset_counts()
        assert score.get_compliance_percentage() == 100.0  # No vulnerabilities = compliant

    def test_is_compliant(self):
        """Test compliance checking."""
        score = ChecklistScore()
        checklist_id = uuid.uuid4()

        score.create_score(checklist_id, None, "test-server", "Windows Server 2019")

        # 90% compliant should pass default threshold (80%)
        score.totalCat1NotAFinding = 9
        score.totalCat1Open = 1
        assert score.is_compliant()  # 90% >= 80%

        # 70% compliant should fail default threshold
        score.reset_counts()
        score.totalCat1NotAFinding = 7
        score.totalCat1Open = 3
        assert not score.is_compliant()  # 70% < 80%

        # Custom threshold
        assert score.is_compliant(65.0)  # 70% >= 65%

    def test_has_critical_findings(self):
        """Test critical findings check."""
        score = ChecklistScore()
        checklist_id = uuid.uuid4()

        score.create_score(checklist_id, None, "test-server", "Windows Server 2019")

        assert not score.has_critical_findings()

        score.totalCat1Open = 1
        assert score.has_critical_findings()

    def test_get_score_summary(self):
        """Test score summary generation."""
        score = ChecklistScore()
        checklist_id = uuid.uuid4()

        score.create_score(checklist_id, None, "test-server", "Windows Server 2019")

        score.totalCat1Open = 1
        score.totalCat1NotAFinding = 2
        score.totalCat2Open = 1
        score.totalCat2NotAFinding = 1

        summary = score.get_score_summary()

        assert summary['total_open'] == 2
        assert summary['total_not_a_finding'] == 3
        assert summary['total_vulnerabilities'] == 5

        assert summary['categories']['cat1']['open'] == 1
        assert summary['categories']['cat1']['not_a_finding'] == 2
        assert summary['categories']['cat2']['open'] == 1
        assert summary['categories']['cat2']['not_a_finding'] == 1

    def test_update_system_assignment(self):
        """Test updating system group assignment."""
        score = ChecklistScore()
        checklist_id = uuid.uuid4()

        score.create_score(checklist_id, None, "test-server", "Windows Server 2019")

        system_id = uuid.uuid4()
        score.update_system_assignment(system_id)

        assert score.systemGroupId == system_id

    def test_str_representation(self):
        """Test string representation."""
        score = ChecklistScore()
        checklist_id = uuid.uuid4()

        score.create_score(checklist_id, None, "test-server", "Windows Server 2019")

        expected = f"ChecklistScore({score.id}): test-server - Windows Server 2019"
        assert str(score) == expected
