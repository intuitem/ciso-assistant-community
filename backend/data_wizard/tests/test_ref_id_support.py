"""
Tests for ref_id support in the Data Wizard.

Coverage:
  A. Base find_existing — priority: ref_id first, name as fallback
  B. _resolve_vulnerabilities — ref_id lookup before name / get_or_create
  C. VulnerabilityRecordConsumer relational resolvers — ref_id fallback
"""

import pytest

from core.models import AppliedControl, Asset, SecurityException, Vulnerability
from iam.models import Folder

from data_wizard.views import (
    _resolve_vulnerabilities,
    AppliedControlRecordConsumer,
    VulnerabilityRecordConsumer,
)


# ─────────────────────────────────────────────────────────────────────────────
# A. Base find_existing — ref_id priority over name
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFindExistingRefIdPriority:
    """AppliedControl is used as the representative model throughout."""

    def test_matches_by_ref_id_even_when_name_differs(
        self, base_context, domain_folder
    ):
        existing = AppliedControl.objects.create(
            name="Old Name", ref_id="AC-001", folder=domain_folder
        )
        consumer = AppliedControlRecordConsumer(base_context)
        found = consumer.find_existing(
            {
                "ref_id": "AC-001",
                "name": "Completely Different Name",
                "folder": str(domain_folder.id),
            }
        )
        assert found is not None and found.id == existing.id

    def test_matches_by_name_when_ref_id_absent(self, base_context, domain_folder):
        existing = AppliedControl.objects.create(
            name="Firewall Rule", ref_id="AC-002", folder=domain_folder
        )
        consumer = AppliedControlRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "", "name": "Firewall Rule", "folder": str(domain_folder.id)}
        )
        assert found is not None and found.id == existing.id

    def test_falls_back_to_name_when_ref_id_unknown(self, base_context, domain_folder):
        existing = AppliedControl.objects.create(
            name="Patch Management", ref_id="AC-003", folder=domain_folder
        )
        consumer = AppliedControlRecordConsumer(base_context)
        # ref_id doesn't match anything; name matches → should still find it
        found = consumer.find_existing(
            {
                "ref_id": "NO-SUCH-REF",
                "name": "Patch Management",
                "folder": str(domain_folder.id),
            }
        )
        assert found is not None and found.id == existing.id

    def test_returns_none_when_neither_ref_id_nor_name_match(
        self, base_context, domain_folder
    ):
        AppliedControl.objects.create(
            name="Real Control", ref_id="AC-004", folder=domain_folder
        )
        consumer = AppliedControlRecordConsumer(base_context)
        found = consumer.find_existing(
            {
                "ref_id": "GHOST",
                "name": "Ghost Control",
                "folder": str(domain_folder.id),
            }
        )
        assert found is None

    def test_folder_scoped_lookup_does_not_match_other_folder(
        self, base_context, domain_folder
    ):
        other_folder = Folder.objects.create(name="Other Domain")
        AppliedControl.objects.create(
            name="Shared Name", ref_id="AC-005", folder=other_folder
        )
        consumer = AppliedControlRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "AC-005", "name": "Shared Name", "folder": str(domain_folder.id)}
        )
        assert found is None

    def test_ref_id_wins_when_name_would_match_different_record(
        self, base_context, domain_folder
    ):
        ac_a = AppliedControl.objects.create(
            name="Old Name", ref_id="AC-X", folder=domain_folder
        )
        AppliedControl.objects.create(
            name="New Name", ref_id="AC-Y", folder=domain_folder
        )
        consumer = AppliedControlRecordConsumer(base_context)
        # ref_id points to ac_a; name points to the second record — ref_id must win
        found = consumer.find_existing(
            {"ref_id": "AC-X", "name": "New Name", "folder": str(domain_folder.id)}
        )
        assert found is not None and found.id == ac_a.id


# ─────────────────────────────────────────────────────────────────────────────
# B. _resolve_vulnerabilities — ref_id lookup, name fallback, create-on-miss
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestResolveVulnerabilities:
    def test_matches_existing_vuln_by_ref_id(self, domain_folder):
        existing = Vulnerability.objects.create(
            name="OpenSSL Heap Overflow", ref_id="CVE-2024-1234", folder=domain_folder
        )
        ids, failed = _resolve_vulnerabilities("CVE-2024-1234", domain_folder)
        assert failed == []
        assert ids == [existing.id]
        # Must not create a duplicate
        assert Vulnerability.objects.filter(folder=domain_folder).count() == 1

    def test_matches_existing_vuln_by_name_when_no_ref_id(self, domain_folder):
        existing = Vulnerability.objects.create(
            name="My Known Vuln", ref_id="", folder=domain_folder
        )
        ids, failed = _resolve_vulnerabilities("My Known Vuln", domain_folder)
        assert failed == []
        assert ids == [existing.id]
        assert Vulnerability.objects.filter(folder=domain_folder).count() == 1

    def test_creates_new_vuln_when_not_found(self, domain_folder):
        ids, failed = _resolve_vulnerabilities("Brand New Vuln", domain_folder)
        assert failed == []
        assert len(ids) == 1
        assert Vulnerability.objects.filter(
            name="Brand New Vuln", folder=domain_folder
        ).exists()

    def test_resolves_multiple_values_pipe_separated(self, domain_folder):
        v1 = Vulnerability.objects.create(
            name="Vuln A", ref_id="CVE-A", folder=domain_folder
        )
        v2 = Vulnerability.objects.create(
            name="Vuln B", ref_id="CVE-B", folder=domain_folder
        )
        ids, failed = _resolve_vulnerabilities("CVE-A|CVE-B", domain_folder)
        assert failed == []
        assert set(ids) == {v1.id, v2.id}

    def test_ref_id_lookup_is_folder_scoped(self, domain_folder):
        other_folder = Folder.objects.create(name="Other Domain")
        Vulnerability.objects.create(
            name="Shared Vuln", ref_id="CVE-SHARED", folder=other_folder
        )
        _, failed = _resolve_vulnerabilities("CVE-SHARED", domain_folder)
        # Should NOT find the one in the other folder, so creates a new one
        assert failed == []
        assert Vulnerability.objects.filter(folder=domain_folder).count() == 1
        assert Vulnerability.objects.filter(folder=other_folder).count() == 1


# ─────────────────────────────────────────────────────────────────────────────
# C. VulnerabilityRecordConsumer — relational resolvers use ref_id fallback
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVulnerabilityConsumerRelationalResolvers:
    def test_applied_control_resolved_by_ref_id(self, base_context, domain_folder):
        ac = AppliedControl.objects.create(
            name="Patch Management", ref_id="AC-PATCH-01", folder=domain_folder
        )
        consumer = VulnerabilityRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Test Vuln", "applied_controls": "AC-PATCH-01"}, None
        )
        assert error is None
        assert ac.id in record_data["applied_controls"]

    def test_asset_resolved_by_ref_id(self, base_context, domain_folder):
        asset = Asset.objects.create(
            name="Web Server", ref_id="AST-WEB-01", folder=domain_folder
        )
        consumer = VulnerabilityRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Test Vuln", "assets": "AST-WEB-01"}, None
        )
        assert error is None
        assert asset.id in record_data["assets"]

    def test_security_exception_resolved_by_ref_id(self, base_context, domain_folder):
        se = SecurityException.objects.create(
            name="Firewall Exception", ref_id="SE-FW-01", folder=domain_folder
        )
        consumer = VulnerabilityRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Test Vuln", "security_exceptions": "SE-FW-01"}, None
        )
        assert error is None
        assert se.id in record_data["security_exceptions"]

    def test_applied_control_still_works_by_name(self, base_context, domain_folder):
        ac = AppliedControl.objects.create(
            name="Antivirus", ref_id="", folder=domain_folder
        )
        consumer = VulnerabilityRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Test Vuln", "applied_controls": "Antivirus"}, None
        )
        assert error is None
        assert ac.id in record_data["applied_controls"]

    def test_error_when_applied_control_not_found(self, base_context):
        consumer = VulnerabilityRecordConsumer(base_context)
        _, error = consumer.prepare_create(
            {"name": "Test Vuln", "applied_controls": "GHOST-CONTROL"}, None
        )
        assert error is not None
        assert "GHOST-CONTROL" in error.error
