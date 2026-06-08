"""
Unit + integration tests for all RecordConsumer subclasses.

Tests are grouped by consumer. Each group covers:
  - Missing required fields → Error returned
  - Happy path → correct record_data dict
  - Consumer-specific field mappings / normalizations
  - find_existing behaviour (ref_id priority, name fallback, folder scope)
  - Conflict modes (STOP / SKIP / UPDATE) via process_records
"""

import pytest
from unittest.mock import patch, MagicMock

from core.models import (
    Actor,
    AppliedControl,
    Asset,
    Evidence,
    FindingsAssessment,
    Incident,
    Perimeter,
    ReferenceControl,
    SecurityException,
    Threat,
    Vulnerability,
)
from iam.models import Folder, User

from data_wizard.views import (
    AppliedControlRecordConsumer,
    AssetRecordConsumer,
    BaseContext,
    ConflictMode,
    ElementaryActionRecordConsumer,
    EvidenceRecordConsumer,
    FindingsAssessmentRecordConsumer,
    FolderRecordConsumer,
    IncidentRecordConsumer,
    PerimeterRecordConsumer,
    PolicyRecordConsumer,
    ProcessingRecordConsumer,
    ReferenceControlRecordConsumer,
    SecurityExceptionRecordConsumer,
    ThreatRecordConsumer,
    UserRecordConsumer,
    VulnerabilityRecordConsumer,
    _resolve_filtering_labels,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _run(consumer_cls, context, records):
    """Call process_records patching out RoleAssignment permission check."""

    def _all_ids(root_folder, user, model_class):
        ids = list(model_class.objects.values_list("id", flat=True))
        return ids, ids, ids

    with patch(
        "data_wizard.views.RoleAssignment.get_accessible_object_ids",
        side_effect=_all_ids,
    ):
        return consumer_cls(context).process_records(records)


# ─────────────────────────────────────────────────────────────────────────────
# _resolve_filtering_labels
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestResolveFilteringLabels:
    def test_empty_value_returns_empty_list(self):
        assert _resolve_filtering_labels("") == []

    def test_none_returns_empty_list(self):
        assert _resolve_filtering_labels(None) == []

    def test_comma_separated_creates_and_returns_ids(self):
        ids = _resolve_filtering_labels("critical,needs-review")
        assert len(ids) == 2

    def test_pipe_separated_creates_and_returns_ids(self):
        ids = _resolve_filtering_labels("critical|needs-review")
        assert len(ids) == 2

    def test_existing_label_not_duplicated(self):
        from core.models import FilteringLabel

        FilteringLabel.objects.create(label="existing-label")
        ids = _resolve_filtering_labels("existing-label")
        assert len(ids) == 1
        assert FilteringLabel.objects.filter(label="existing-label").count() == 1


# ─────────────────────────────────────────────────────────────────────────────
# AssetRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAssetConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = AssetRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, [1, 2, 3, 4])
        assert error is not None
        assert "Name" in error.error

    def test_happy_path_primary_asset(self, base_context, domain_folder):
        consumer = AssetRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Web App", "type": "primary", "ref_id": "AST-001"}, [1, 2, 3, 4]
        )
        assert error is None
        assert record_data["name"] == "Web App"
        assert record_data["type"] == "PR"
        assert record_data["ref_id"] == "AST-001"

    def test_type_mapping_support(self, base_context):
        consumer = AssetRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "DB Server", "type": "support"}, [1, 2, 3, 4]
        )
        assert record_data["type"] == "SP"

    def test_type_defaults_to_sp(self, base_context):
        consumer = AssetRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create({"name": "X"}, [1, 2, 3, 4])
        assert record_data["type"] == "SP"

    def test_link_alias_accepted(self, base_context):
        consumer = AssetRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "X", "link": "https://example.com"}, [1, 2, 3, 4]
        )
        assert record_data["reference_link"] == "https://example.com"

    def test_domain_column_resolves_folder(self, base_context, domain_folder):
        consumer = AssetRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "X", "domain": "Test Domain"}, [1, 2, 3, 4]
        )
        assert str(record_data["folder"]) == str(domain_folder.id)

    def test_second_pass_links_parent_asset(
        self, base_context, domain_folder, all_accessible
    ):
        result = _run(
            AssetRecordConsumer,
            base_context,
            [
                {"name": "Parent", "ref_id": "PAR-1"},
                {"name": "Child", "ref_id": "CHI-1", "parent_assets": "PAR-1"},
            ],
        )
        assert result.created == 2
        child = Asset.objects.get(ref_id="CHI-1")
        parent = Asset.objects.get(ref_id="PAR-1")
        assert parent in child.parent_assets.all()

    def test_unparseable_security_objectives_yields_warning(self, base_context):
        consumer = AssetRecordConsumer(base_context)
        _, error = consumer.prepare_create(
            {"name": "X", "type": "primary", "security_objectives": "bad_format"},
            [1, 2, 3, 4],
        )
        assert error is not None
        assert error.is_warning is True


# ─────────────────────────────────────────────────────────────────────────────
# AppliedControlRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAppliedControlConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = AppliedControlRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, MagicMock())
        assert error is not None

    def test_happy_path(self, base_context, domain_folder):
        consumer = AppliedControlRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Patch Policy", "ref_id": "AC-001", "effort": "M"}, MagicMock()
        )
        assert error is None
        assert record_data["name"] == "Patch Policy"
        assert record_data["ref_id"] == "AC-001"
        assert record_data["effort"] == "M"

    def test_effort_normalization(self, base_context):
        consumer = AppliedControlRecordConsumer(base_context)
        for raw, expected in [("extra small", "XS"), ("large", "L"), ("XL", "XL")]:
            record_data, _ = consumer.prepare_create(
                {"name": "X", "effort": raw}, MagicMock()
            )
            assert record_data["effort"] == expected

    def test_impact_text_mapping(self, base_context):
        consumer = AppliedControlRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "X", "control_impact": "very high"}, MagicMock()
        )
        assert record_data["control_impact"] == 5

    def test_impact_alias_column(self, base_context):
        consumer = AppliedControlRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "X", "impact": "3"}, MagicMock()
        )
        assert record_data["control_impact"] == 3

    def test_out_of_range_impact_excluded(self, base_context):
        consumer = AppliedControlRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "X", "control_impact": "9"}, MagicMock()
        )
        assert record_data.get("control_impact") is None

    def test_reference_control_linked_by_ref_id(self, base_context, domain_folder):
        from core.models import ReferenceControl

        rc = ReferenceControl.objects.create(
            name="Access Control Policy", ref_id="RC-001", folder=domain_folder
        )
        consumer = AppliedControlRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "AC", "reference_control": "RC-001"}, MagicMock()
        )
        assert error is None
        assert record_data["reference_control"] == rc.id

    def test_csf_function_lowercased(self, base_context):
        consumer = AppliedControlRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "X", "csf_function": "PROTECT"}, MagicMock()
        )
        assert record_data["csf_function"] == "protect"

    def test_find_existing_by_ref_id(self, base_context, domain_folder):
        existing = AppliedControl.objects.create(
            name="Old Name", ref_id="AC-FIND", folder=domain_folder
        )
        consumer = AppliedControlRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "AC-FIND", "name": "New Name", "folder": str(domain_folder.id)}
        )
        assert found.id == existing.id

    def test_find_existing_by_name_fallback(self, base_context, domain_folder):
        existing = AppliedControl.objects.create(
            name="My Control", folder=domain_folder
        )
        consumer = AppliedControlRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "", "name": "My Control", "folder": str(domain_folder.id)}
        )
        assert found.id == existing.id

    def test_find_existing_returns_none_when_no_match(
        self, base_context, domain_folder
    ):
        consumer = AppliedControlRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "GHOST", "name": "Ghost", "folder": str(domain_folder.id)}
        )
        assert found is None


# ─────────────────────────────────────────────────────────────────────────────
# Conflict modes — tested on AppliedControl as representative
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestConflictModes:
    def _record(self):
        return {"name": "Firewall Rule", "ref_id": "AC-CF-01", "description": "v1"}

    def test_stop_mode_halts_on_duplicate(
        self, base_context, domain_folder, all_accessible
    ):
        AppliedControl.objects.create(
            name="Firewall Rule", ref_id="AC-CF-01", folder=domain_folder
        )
        result = _run(AppliedControlRecordConsumer, base_context, [self._record()])
        assert result.stopped is True
        assert result.failed == 1
        assert result.created == 0

    def test_skip_mode_skips_duplicate(
        self, skip_context, domain_folder, all_accessible
    ):
        AppliedControl.objects.create(
            name="Firewall Rule", ref_id="AC-CF-01", folder=domain_folder
        )
        result = _run(AppliedControlRecordConsumer, skip_context, [self._record()])
        assert result.skipped == 1
        assert result.created == 0
        assert result.stopped is False

    def test_update_mode_updates_existing(
        self, update_context, domain_folder, all_accessible
    ):
        existing = AppliedControl.objects.create(
            name="Firewall Rule",
            ref_id="AC-CF-01",
            folder=domain_folder,
            description="old desc",
        )
        updated_record = {
            "name": "Firewall Rule",
            "ref_id": "AC-CF-01",
            "description": "new desc",
        }
        result = _run(AppliedControlRecordConsumer, update_context, [updated_record])
        assert result.updated == 1
        existing.refresh_from_db()
        assert existing.description == "new desc"

    def test_stop_mode_creates_when_no_conflict(
        self, base_context, domain_folder, all_accessible
    ):
        result = _run(AppliedControlRecordConsumer, base_context, [self._record()])
        assert result.created == 1
        assert result.stopped is False

    def test_multiple_records_stop_after_first_conflict(
        self, base_context, domain_folder, all_accessible
    ):
        AppliedControl.objects.create(
            name="Firewall Rule", ref_id="AC-CF-01", folder=domain_folder
        )
        records = [self._record(), {"name": "Other", "ref_id": "AC-CF-02"}]
        result = _run(AppliedControlRecordConsumer, base_context, records)
        assert result.stopped is True
        # Only 1 error, second record never processed
        assert result.failed == 1


# ─────────────────────────────────────────────────────────────────────────────
# EvidenceRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEvidenceConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = EvidenceRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, None)
        assert error is not None

    def test_happy_path(self, base_context, domain_folder):
        consumer = EvidenceRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Audit Log", "description": "2024 logs"}, None
        )
        assert error is None
        assert record_data["name"] == "Audit Log"

    def test_find_existing_by_name(self, base_context, domain_folder):
        existing = Evidence.objects.create(name="Audit Log", folder=domain_folder)
        consumer = EvidenceRecordConsumer(base_context)
        found = consumer.find_existing(
            {"name": "Audit Log", "folder": str(domain_folder.id)}
        )
        assert found.id == existing.id


# ─────────────────────────────────────────────────────────────────────────────
# UserRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestUserConsumer:
    def test_missing_email_returns_error(self, base_context):
        consumer = UserRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, None)
        assert error is not None
        assert "email" in error.error.lower()

    def test_happy_path(self, base_context):
        consumer = UserRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"email": "alice@example.com", "first_name": "Alice", "last_name": "Smith"},
            None,
        )
        assert error is None
        assert record_data["email"] == "alice@example.com"
        assert record_data["first_name"] == "Alice"

    def test_find_existing_by_email_case_insensitive(self, base_context, root_folder):
        existing = User.objects.create_user("Bob@Example.com")
        consumer = UserRecordConsumer(base_context)
        found = consumer.find_existing({"email": "bob@example.com"})
        assert found.id == existing.id

    def test_find_existing_returns_none_for_unknown_email(self, base_context):
        consumer = UserRecordConsumer(base_context)
        found = consumer.find_existing({"email": "ghost@example.com"})
        assert found is None


# ─────────────────────────────────────────────────────────────────────────────
# PerimeterRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPerimeterConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = PerimeterRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, None)
        assert error is not None

    def test_happy_path(self, base_context, domain_folder):
        consumer = PerimeterRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "ERP Project", "ref_id": "PRM-001"}, None
        )
        assert error is None
        assert record_data["name"] == "ERP Project"
        assert record_data["ref_id"] == "PRM-001"

    def test_status_alias_lc_status(self, base_context):
        consumer = PerimeterRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "X", "status": "in_prod"}, None
        )
        assert error is None
        assert record_data["lc_status"] == "in_prod"

    def test_invalid_status_returns_error(self, base_context):
        consumer = PerimeterRecordConsumer(base_context)
        _, error = consumer.prepare_create(
            {"name": "X", "lc_status": "invalid_state"}, None
        )
        assert error is not None

    def test_find_existing_by_ref_id(self, base_context, domain_folder):
        existing = Perimeter.objects.create(
            name="Old Perimeter", ref_id="PRM-FIND", folder=domain_folder
        )
        consumer = PerimeterRecordConsumer(base_context)
        found = consumer.find_existing(
            {
                "ref_id": "PRM-FIND",
                "name": "Different Name",
                "folder": str(domain_folder.id),
            }
        )
        assert found.id == existing.id


# ─────────────────────────────────────────────────────────────────────────────
# ThreatRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestThreatConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = ThreatRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, None)
        assert error is not None

    def test_happy_path(self, base_context, domain_folder):
        consumer = ThreatRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Ransomware", "ref_id": "THR-001"}, None
        )
        assert error is None
        assert record_data["name"] == "Ransomware"


# ─────────────────────────────────────────────────────────────────────────────
# ReferenceControlRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestReferenceControlConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = ReferenceControlRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, None)
        assert error is not None

    def test_happy_path(self, base_context, domain_folder):
        consumer = ReferenceControlRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Access Control", "ref_id": "RC-001", "category": "technical"},
            None,
        )
        assert error is None
        assert record_data["category"] == "technical"

    def test_function_alias_maps_to_csf_function(self, base_context):
        consumer = ReferenceControlRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "X", "function": "protect"}, None
        )
        assert record_data["csf_function"] == "protect"

    def test_governance_alias_normalised(self, base_context):
        consumer = ReferenceControlRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "X", "function": "governance"}, None
        )
        assert record_data["csf_function"] == "govern"


# ─────────────────────────────────────────────────────────────────────────────
# SecurityExceptionRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSecurityExceptionConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = SecurityExceptionRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, None)
        assert error is not None

    def test_happy_path(self, base_context, domain_folder):
        consumer = SecurityExceptionRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Legacy DB Exception", "ref_id": "SE-001", "severity": "high"},
            None,
        )
        assert error is None
        assert record_data["severity"] == 3

    def test_severity_info_maps_to_zero(self, base_context):
        consumer = SecurityExceptionRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "X", "severity": "info"}, None
        )
        assert record_data["severity"] == 0

    def test_status_normalization(self, base_context):
        consumer = SecurityExceptionRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "X", "status": "in review"}, None
        )
        assert record_data["status"] == "in_review"

    def test_find_existing_by_ref_id(self, base_context, domain_folder):
        existing = SecurityException.objects.create(
            name="Old Name", ref_id="SE-FIND", folder=domain_folder
        )
        consumer = SecurityExceptionRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "SE-FIND", "name": "New Name", "folder": str(domain_folder.id)}
        )
        assert found.id == existing.id


# ─────────────────────────────────────────────────────────────────────────────
# IncidentRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestIncidentConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = IncidentRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, None)
        assert error is not None

    def test_happy_path(self, base_context, domain_folder):
        consumer = IncidentRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Data Breach", "severity": "critical", "status": "new"}, None
        )
        assert error is None
        assert record_data["severity"] == 1
        assert record_data["status"] == "new"

    def test_severity_aliases(self, base_context):
        consumer = IncidentRecordConsumer(base_context)
        for alias, expected in [("sev1", 1), ("major", 2), ("sev3", 3)]:
            record_data, _ = consumer.prepare_create(
                {"name": "X", "severity": alias}, None
            )
            assert record_data["severity"] == expected

    def test_status_aliases(self, base_context):
        consumer = IncidentRecordConsumer(base_context)
        for alias, expected in [("in progress", "ongoing"), ("in_progress", "ongoing")]:
            record_data, _ = consumer.prepare_create(
                {"name": "X", "status": alias}, None
            )
            assert record_data["status"] == expected

    def test_detection_mapping(self, base_context):
        consumer = IncidentRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create(
            {"name": "X", "detection": "internal"}, None
        )
        assert record_data["detection"] == "internally_detected"

    def test_find_existing_by_ref_id(self, base_context, domain_folder):
        existing = Incident.objects.create(
            name="Old Breach", ref_id="INC-FIND", folder=domain_folder
        )
        consumer = IncidentRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "INC-FIND", "name": "Different", "folder": str(domain_folder.id)}
        )
        assert found.id == existing.id


# ─────────────────────────────────────────────────────────────────────────────
# VulnerabilityRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVulnerabilityConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = VulnerabilityRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, None)
        assert error is not None

    def test_happy_path(self, base_context, domain_folder):
        consumer = VulnerabilityRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Log4Shell", "ref_id": "CVE-2021-44228", "severity": "critical"},
            None,
        )
        assert error is None
        assert record_data["ref_id"] == "CVE-2021-44228"
        assert record_data["severity"] == 4

    def test_applied_controls_resolved_by_name(self, base_context, domain_folder):
        ac = AppliedControl.objects.create(name="Patch Log4j", folder=domain_folder)
        consumer = VulnerabilityRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "X", "applied_controls": "Patch Log4j"}, None
        )
        assert error is None
        assert ac.id in record_data["applied_controls"]

    def test_applied_controls_resolved_by_ref_id(self, base_context, domain_folder):
        ac = AppliedControl.objects.create(
            name="Patch", ref_id="AC-LOG4J", folder=domain_folder
        )
        consumer = VulnerabilityRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "X", "applied_controls": "AC-LOG4J"}, None
        )
        assert error is None
        assert ac.id in record_data["applied_controls"]

    def test_applied_controls_not_found_returns_error(
        self, base_context, domain_folder
    ):
        consumer = VulnerabilityRecordConsumer(base_context)
        _, error = consumer.prepare_create(
            {"name": "X", "applied_controls": "Nonexistent"}, None
        )
        assert error is not None
        assert "Nonexistent" in error.error

    def test_assets_resolved_by_ref_id(self, base_context, domain_folder):
        asset = Asset.objects.create(
            name="Server", ref_id="AST-SRV", folder=domain_folder
        )
        consumer = VulnerabilityRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "X", "assets": "AST-SRV"}, None
        )
        assert error is None
        assert asset.id in record_data["assets"]

    def test_security_exceptions_resolved_by_ref_id(self, base_context, domain_folder):
        se = SecurityException.objects.create(
            name="FW Exception", ref_id="SE-FW", folder=domain_folder
        )
        consumer = VulnerabilityRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "X", "security_exceptions": "SE-FW"}, None
        )
        assert error is None
        assert se.id in record_data["security_exceptions"]

    def test_find_existing_by_ref_id(self, base_context, domain_folder):
        existing = Vulnerability.objects.create(
            name="Log4Shell", ref_id="CVE-2021-44228", folder=domain_folder
        )
        consumer = VulnerabilityRecordConsumer(base_context)
        found = consumer.find_existing(
            {
                "ref_id": "CVE-2021-44228",
                "name": "Different Name",
                "folder": str(domain_folder.id),
            }
        )
        assert found.id == existing.id

    def test_find_existing_by_name_fallback(self, base_context, domain_folder):
        existing = Vulnerability.objects.create(name="Log4Shell", folder=domain_folder)
        consumer = VulnerabilityRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "", "name": "Log4Shell", "folder": str(domain_folder.id)}
        )
        assert found.id == existing.id

    def test_status_mapping(self, base_context):
        consumer = VulnerabilityRecordConsumer(base_context)
        for raw, expected in [
            ("fixed", "fixed"),
            ("not exploitable", "not_exploitable"),
            ("unaffected", "unaffected"),
        ]:
            record_data, _ = consumer.prepare_create({"name": "X", "status": raw}, None)
            assert record_data["status"] == expected


# ─────────────────────────────────────────────────────────────────────────────
# PolicyRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPolicyConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = PolicyRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, MagicMock())
        assert error is not None

    def test_happy_path(self, base_context, domain_folder):
        consumer = PolicyRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Data Classification Policy", "ref_id": "POL-001"}, MagicMock()
        )
        assert error is None
        assert record_data["name"] == "Data Classification Policy"

    def test_default_status_is_to_do(self, base_context):
        consumer = PolicyRecordConsumer(base_context)
        record_data, _ = consumer.prepare_create({"name": "X"}, MagicMock())
        assert record_data["status"] == "to_do"


# ─────────────────────────────────────────────────────────────────────────────
# ElementaryActionRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestElementaryActionConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = ElementaryActionRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, None)
        assert error is not None

    def test_happy_path(self, base_context):
        consumer = ElementaryActionRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Phishing Email", "ref_id": "EA-001"}, None
        )
        assert error is None
        assert record_data["name"] == "Phishing Email"

    def test_find_existing_by_ref_id(self, base_context, domain_folder):
        from ebios_rm.models import ElementaryAction

        existing = ElementaryAction.objects.create(
            name="Old Name", ref_id="EA-FIND", folder=domain_folder
        )
        consumer = ElementaryActionRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "EA-FIND", "name": "New Name", "folder": str(domain_folder.id)}
        )
        assert found.id == existing.id


# ─────────────────────────────────────────────────────────────────────────────
# ProcessingRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProcessingConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = ProcessingRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, None)
        assert error is not None

    def test_happy_path(self, base_context):
        consumer = ProcessingRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "HR Payroll Processing", "ref_id": "PRC-001"}, None
        )
        assert error is None
        assert record_data["name"] == "HR Payroll Processing"

    def test_find_existing_by_ref_id(self, base_context, domain_folder):
        from privacy.models import Processing

        existing = Processing.objects.create(
            name="Old Processing", ref_id="PRC-FIND", folder=domain_folder
        )
        consumer = ProcessingRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "PRC-FIND", "name": "Different", "folder": str(domain_folder.id)}
        )
        assert found.id == existing.id


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────


class TestResultDataclass:
    def test_successful_is_created_plus_updated(self):
        from data_wizard.views import Result

        r = Result(created=3, updated=2)
        assert r.successful == 5

    def test_to_dict_excludes_empty_warnings(self):
        from data_wizard.views import Result

        r = Result(created=1)
        d = r.to_dict()
        assert "warnings" not in d

    def test_to_dict_includes_warnings_when_present(self):
        from data_wizard.views import Result, Error

        r = Result()
        r.warnings.append(Error(record={}, error="warn", is_warning=True))
        d = r.to_dict()
        assert "warnings" in d
        assert len(d["warnings"]) == 1

    def test_add_error_increments_failed(self):
        from data_wizard.views import Result, Error

        r = Result()
        r.add_error(Error(record={}, error="oops"))
        assert r.failed == 1

    def test_add_error_with_custom_fail_count(self):
        from data_wizard.views import Result, Error

        r = Result()
        r.add_error(Error(record={}, error="oops"), fail_count=5)
        assert r.failed == 5


# ─────────────────────────────────────────────────────────────────────────────
# FolderRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFolderConsumer:
    def test_missing_name_returns_error(self, base_context):
        consumer = FolderRecordConsumer(base_context)
        record_data, error = consumer.prepare_create({}, None)
        assert error is not None
        assert "mandatory" in error.error.lower()

    def test_unknown_parent_returns_error(self, base_context):
        consumer = FolderRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "New", "domain": "DoesNotExist"}, None
        )
        assert error is not None
        assert "not found" in error.error

    def test_ambiguous_parent_returns_error(
        self, base_context, root_folder, other_folder
    ):
        # Two folders with the same name under different parents — triggers ambiguity.
        Folder.objects.create(
            name="Shared",
            parent_folder=root_folder,
            content_type=Folder.ContentType.DOMAIN,
        )
        Folder.objects.create(
            name="Shared",
            parent_folder=other_folder,
            content_type=Folder.ContentType.DOMAIN,
        )
        consumer = FolderRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Child", "domain": "Shared"}, None
        )
        assert error is not None
        assert "Multiple" in error.error

    def test_no_domain_uses_root_folder(self, base_context, root_folder):
        consumer = FolderRecordConsumer(base_context)
        record_data, error = consumer.prepare_create({"name": "TopLevel"}, None)
        assert error is None
        assert record_data["parent_folder"] == root_folder.id

    def test_valid_domain_resolves_parent(self, base_context, domain_folder):
        consumer = FolderRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Child", "domain": domain_folder.name}, None
        )
        assert error is None
        assert record_data["parent_folder"] == domain_folder.id

    def test_find_existing_by_name_and_parent(self, base_context, domain_folder):
        existing = Folder.objects.create(
            name="Existing Sub",
            parent_folder=domain_folder,
            content_type=Folder.ContentType.DOMAIN,
        )
        consumer = FolderRecordConsumer(base_context)
        found = consumer.find_existing(
            {"name": "Existing Sub", "parent_folder": domain_folder.id}
        )
        assert found is not None
        assert found.id == existing.id

    def test_find_existing_returns_none_when_not_found(self, base_context):
        consumer = FolderRecordConsumer(base_context)
        assert consumer.find_existing({"name": "Ghost"}) is None


# ─────────────────────────────────────────────────────────────────────────────
# FindingsAssessmentRecordConsumer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFindingsAssessmentConsumer:
    def _findings_context(
        self, domain_folder, admin_user, perimeter=None, perimeter_id=None
    ):
        request = MagicMock()
        request.user = admin_user
        request.META = {}
        request.headers.get.return_value = None
        return BaseContext(
            request=request,
            folder_id=str(domain_folder.id),
            folders_map={},
            on_conflict=ConflictMode.STOP,
            perimeter_id=str(perimeter_id or (perimeter.id if perimeter else "")),
        )

    def test_create_context_fails_with_invalid_perimeter(
        self, domain_folder, admin_user
    ):
        ctx = self._findings_context(
            domain_folder,
            admin_user,
            perimeter_id="00000000-0000-0000-0000-000000000000",
        )
        consumer = FindingsAssessmentRecordConsumer(ctx)
        result = _run(
            FindingsAssessmentRecordConsumer,
            ctx,
            [{"name": "Finding A"}, {"name": "Finding B"}],
        )
        assert result.failed == 2
        assert result.created == 0

    def test_happy_path_creates_finding(self, domain_folder, admin_user):
        perimeter = Perimeter.objects.create(
            name="Test Perimeter", folder=domain_folder
        )
        ctx = self._findings_context(domain_folder, admin_user, perimeter=perimeter)
        result = _run(
            FindingsAssessmentRecordConsumer,
            ctx,
            [
                {
                    "name": "SQL Injection",
                    "severity": "high",
                    "ref_id": "FIND-001",
                    "status": "identified",
                }
            ],
        )
        assert result.created == 1
        assert FindingsAssessment.objects.filter(folder=domain_folder).exists()


# ─────────────────────────────────────────────────────────────────────────────
# VulnerabilityRecordConsumer — pipe/comma multi-value M2M
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVulnerabilityPipeSeparatedM2M:
    def test_pipe_separated_applied_controls_resolved(
        self, base_context, domain_folder
    ):
        ac1 = AppliedControl.objects.create(
            name="Patch A", ref_id="AC-P1", folder=domain_folder
        )
        ac2 = AppliedControl.objects.create(
            name="Patch B", ref_id="AC-P2", folder=domain_folder
        )
        consumer = VulnerabilityRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Vuln", "applied_controls": "AC-P1|AC-P2"}, None
        )
        assert error is None
        assert ac1.id in record_data["applied_controls"]
        assert ac2.id in record_data["applied_controls"]

    def test_comma_separated_assets_resolved(self, base_context, domain_folder):
        a1 = Asset.objects.create(
            name="Server A", ref_id="AST-A1", folder=domain_folder
        )
        a2 = Asset.objects.create(
            name="Server B", ref_id="AST-A2", folder=domain_folder
        )
        consumer = VulnerabilityRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "Vuln", "assets": "AST-A1,AST-A2"}, None
        )
        assert error is None
        assert a1.id in record_data["assets"]
        assert a2.id in record_data["assets"]


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE mode: M2M owner clear + serializer validation stopped flag
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestUpdateModeEdgeCases:
    def test_empty_owner_column_clears_existing_owners(
        self, update_context, domain_folder, admin_user
    ):
        ac = AppliedControl.objects.create(
            name="Firewall Rule", ref_id="AC-OWN-01", folder=domain_folder
        )
        actor, _ = Actor.objects.get_or_create(user=admin_user)
        ac.owner.add(actor)
        assert ac.owner.count() == 1

        _run(
            AppliedControlRecordConsumer,
            update_context,
            [{"name": "Firewall Rule", "ref_id": "AC-OWN-01", "owner": ""}],
        )

        ac.refresh_from_db()
        assert ac.owner.count() == 0

    def test_update_serializer_validation_failure_continues_processing(
        self, update_context, domain_folder
    ):
        AppliedControl.objects.create(
            name="Existing AC", ref_id="AC-STOP-01", folder=domain_folder
        )
        # UPDATE mode: a serializer validation failure records the error and
        # continues to the next record — stopped must remain False.
        result = _run(
            AppliedControlRecordConsumer,
            update_context,
            [
                {
                    "name": "Existing AC",
                    "ref_id": "AC-STOP-01",
                    "status": "INVALID_STATUS_XYZ",
                },
                {"name": "Second Record", "ref_id": "AC-STOP-02"},
            ],
        )
        assert result.stopped is False
        assert result.failed == 1
        assert result.created == 1
