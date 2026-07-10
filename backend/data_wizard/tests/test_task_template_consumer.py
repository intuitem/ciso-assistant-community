"""
Unit + integration tests for the TaskTemplate import flow.

Covers:
  - TaskTemplateRecordConsumer.prepare_create (defaults, booleans, schedule
    parsing/validation, folder-scoped M2M resolution, warnings)
  - find_existing (ref_id priority, name fallback)
  - Conflict modes via process_records, including schedule updates
    (SOURCE_KEY_MAP) and M2M clearing on empty columns
  - LoadFileView multi-sheet Excel import (nodes, roundtrip in STOP mode,
    legacy sheet numbering) and CSV import (BOM + semicolon delimiter)
"""

import pytest
from unittest.mock import MagicMock, patch

from core.models import (
    Actor,
    AppliedControl,
    Asset,
    FindingsAssessment,
    RiskAssessment,
    RiskMatrix,
    TaskNode,
    TaskTemplate,
)

from data_wizard.tests.conftest import make_excel_file
from data_wizard.views import (
    BaseContext,
    ConflictMode,
    TaskTemplateRecordConsumer,
)

URL = "/api/data-wizard/load-file/"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _run(context, records):
    """Call process_records patching out RoleAssignment permission check."""

    def _all_ids(root_folder, user, model_class):
        ids = list(model_class.objects.values_list("id", flat=True))
        return ids, ids, ids

    with patch(
        "data_wizard.views.RoleAssignment.get_accessible_object_ids",
        side_effect=_all_ids,
    ):
        return TaskTemplateRecordConsumer(context).process_records(records)


def _post(client, data: bytes, filename: str, folder_id=None, on_conflict=None):
    headers = {
        "HTTP_X_MODEL_TYPE": "TaskTemplate",
        "HTTP_CONTENT_DISPOSITION": f"attachment; filename={filename}",
        "content_type": "application/octet-stream",
    }
    if folder_id:
        headers["HTTP_X_FOLDER_ID"] = str(folder_id)
    if on_conflict:
        headers["HTTP_X_ON_CONFLICT"] = on_conflict
    return client.post(URL, data=data, **headers)


@pytest.fixture
def two_folder_context(domain_folder, other_folder, admin_user):
    request = MagicMock()
    request.user = admin_user
    return BaseContext(
        request=request,
        folder_id=str(domain_folder.id),
        folders_map={
            "test domain": str(domain_folder.id),
            "other domain": str(other_folder.id),
        },
        on_conflict=ConflictMode.STOP,
    )


# ─────────────────────────────────────────────────────────────────────────────
# prepare_create
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTaskTemplatePrepareCreate:
    def test_missing_name_returns_error(self, base_context):
        consumer = TaskTemplateRecordConsumer(base_context)
        _, error = consumer.prepare_create({}, None)
        assert error is not None
        assert not error.is_warning

    def test_happy_path_defaults(self, base_context, domain_folder):
        consumer = TaskTemplateRecordConsumer(base_context)
        record_data, error = consumer.prepare_create({"name": "Backup check"}, None)
        assert error is None
        assert record_data["name"] == "Backup check"
        assert record_data["is_recurrent"] is False
        assert record_data["enabled"] is True
        assert record_data["folder"] == str(domain_folder.id)
        assert "schedule" not in record_data

    def test_boolean_parsing(self, base_context):
        consumer = TaskTemplateRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {
                "name": "T",
                "is_recurrent": "Yes",
                "enabled": "No",
                "schedule_frequency": "MONTHLY",
                "schedule_interval": "1",
            },
            None,
        )
        assert error is None
        assert record_data["is_recurrent"] is True
        assert record_data["enabled"] is False

    def test_schedule_parsing(self, base_context):
        consumer = TaskTemplateRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {
                "name": "T",
                "is_recurrent": "Yes",
                "schedule_frequency": "weekly",
                "schedule_interval": "2",
                "schedule_days_of_week": "2, 5",
                "schedule_end_date": "2030-12-31",
                "schedule_occurrences": "10",
            },
            None,
        )
        assert error is None
        assert record_data["schedule"] == {
            "frequency": "WEEKLY",
            "interval": 2,
            "days_of_week": [2, 5],
            "end_date": "2030-12-31",
            "occurrences": 10,
        }

    def test_invalid_interval_returns_error(self, base_context):
        consumer = TaskTemplateRecordConsumer(base_context)
        _, error = consumer.prepare_create(
            {"name": "T", "schedule_frequency": "DAILY", "schedule_interval": "abc"},
            None,
        )
        assert error is not None
        assert "schedule_interval" in error.error

    def test_frequency_without_interval_returns_error(self, base_context):
        consumer = TaskTemplateRecordConsumer(base_context)
        _, error = consumer.prepare_create(
            {"name": "T", "schedule_frequency": "DAILY"}, None
        )
        assert error is not None
        assert "together" in error.error

    def test_invalid_days_of_week_returns_error(self, base_context):
        consumer = TaskTemplateRecordConsumer(base_context)
        _, error = consumer.prepare_create(
            {
                "name": "T",
                "schedule_frequency": "WEEKLY",
                "schedule_interval": "1",
                "schedule_days_of_week": "mon,tue",
            },
            None,
        )
        assert error is not None
        assert "schedule_days_of_week" in error.error


@pytest.mark.django_db
class TestTaskTemplateM2MResolution:
    def test_asset_resolved_by_name(self, base_context, domain_folder):
        asset = Asset.objects.create(name="Server", folder=domain_folder)
        consumer = TaskTemplateRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "T", "assets": "server"}, None
        )
        assert error is None
        assert record_data["assets"] == [asset.id]

    def test_applied_control_resolved_by_ref_id(self, base_context, domain_folder):
        ac = AppliedControl.objects.create(
            name="Patch things", ref_id="AC-1", folder=domain_folder
        )
        consumer = TaskTemplateRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "T", "applied_controls": "AC-1"}, None
        )
        assert error is None
        assert record_data["applied_controls"] == [ac.id]

    def test_lookup_scoped_to_accessible_folders(self, base_context, other_folder):
        # other_folder is not in base_context.folders_map → out of scope
        Asset.objects.create(name="Hidden", folder=other_folder)
        consumer = TaskTemplateRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "T", "assets": "Hidden"}, None
        )
        assert record_data["assets"] == []
        assert error is not None
        assert error.is_warning
        assert "Hidden" in error.error

    def test_row_folder_preferred_on_name_collision(
        self, two_folder_context, domain_folder, other_folder
    ):
        Asset.objects.create(name="Shared", folder=domain_folder)
        winner = Asset.objects.create(name="Shared", folder=other_folder)
        consumer = TaskTemplateRecordConsumer(two_folder_context)
        record_data, error = consumer.prepare_create(
            {"name": "T", "folder": "Other Domain", "assets": "Shared"}, None
        )
        assert error is None
        assert record_data["assets"] == [winner.id]

    def test_findings_assessment_resolved_by_plain_name(
        self, base_context, domain_folder
    ):
        # FindingsAssessment.__str__ is the plain name; that is what the export writes.
        fa = FindingsAssessment.objects.create(
            name="Pentest Findings", version="1.0", folder=domain_folder
        )
        consumer = TaskTemplateRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "T", "findings_assessment": "Pentest Findings"}, None
        )
        assert error is None
        assert record_data["findings_assessment"] == [fa.id]

    def test_risk_assessment_version_suffix_resolution(
        self, base_context, domain_folder
    ):
        # RiskAssessment.__str__ is "{name} - {version}"; the export writes that
        # string and the importer must resolve it back.
        matrix = RiskMatrix.objects.create(
            name="test matrix", folder=domain_folder, json_definition={}
        )
        ra = RiskAssessment.objects.create(
            name="Ecommerce Risk overview",
            version="0.1",
            folder=domain_folder,
            risk_matrix=matrix,
        )
        consumer = TaskTemplateRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "T", "risk_assessments": "Ecommerce Risk overview - 0.1"}, None
        )
        assert error is None
        assert record_data["risk_assessments"] == [ra.id]

    def test_assigned_to_resolved_by_email(
        self, base_context, domain_folder, admin_user
    ):
        # User creation auto-syncs an Actor (ActorSyncMixin), so fetch it.
        actor, _ = Actor.objects.get_or_create(user=admin_user)
        consumer = TaskTemplateRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "T", "assigned_to": admin_user.email.upper()}, None
        )
        assert error is None
        assert record_data["assigned_to"] == [actor.id]

    def test_unresolved_assigned_to_yields_warning(self, base_context):
        consumer = TaskTemplateRecordConsumer(base_context)
        record_data, error = consumer.prepare_create(
            {"name": "T", "assigned_to": "ghost@nowhere.test"}, None
        )
        assert record_data["assigned_to"] == []
        assert error is not None
        assert error.is_warning
        assert "ghost@nowhere.test" in error.error


# ─────────────────────────────────────────────────────────────────────────────
# find_existing & conflict modes
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTaskTemplateFindExisting:
    def test_ref_id_has_priority_over_name(self, base_context, domain_folder):
        by_ref = TaskTemplate.objects.create(
            name="Old name", ref_id="TT-1", folder=domain_folder
        )
        TaskTemplate.objects.create(name="New name", folder=domain_folder)
        consumer = TaskTemplateRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "TT-1", "name": "New name", "folder": str(domain_folder.id)}
        )
        assert found.id == by_ref.id

    def test_name_fallback(self, base_context, domain_folder):
        existing = TaskTemplate.objects.create(name="By name", folder=domain_folder)
        consumer = TaskTemplateRecordConsumer(base_context)
        found = consumer.find_existing(
            {"ref_id": "", "name": "By name", "folder": str(domain_folder.id)}
        )
        assert found.id == existing.id


@pytest.mark.django_db
class TestTaskTemplateConflictModes:
    RECORD = {
        "name": "Recurring scan",
        "is_recurrent": "Yes",
        "schedule_frequency": "MONTHLY",
        "schedule_interval": "1",
    }

    def test_create(self, base_context, domain_folder):
        result = _run(base_context, [dict(self.RECORD)])
        assert result.created == 1, result.to_dict()
        template = TaskTemplate.objects.get(name="Recurring scan")
        assert template.schedule["interval"] == 1

    def test_stop_mode_on_duplicate(self, base_context, domain_folder):
        _run(base_context, [dict(self.RECORD)])
        result = _run(base_context, [dict(self.RECORD)])
        assert result.stopped is True
        assert result.failed == 1

    def test_skip_mode_on_duplicate(self, base_context, skip_context, domain_folder):
        _run(base_context, [dict(self.RECORD)])
        result = _run(skip_context, [dict(self.RECORD)])
        assert result.skipped == 1

    def test_update_mode_updates_schedule(
        self, base_context, update_context, domain_folder
    ):
        _run(base_context, [dict(self.RECORD)])
        updated = dict(self.RECORD, schedule_interval="3", schedule_frequency="WEEKLY")
        result = _run(update_context, [updated])
        assert result.updated == 1, result.to_dict()
        template = TaskTemplate.objects.get(name="Recurring scan")
        assert template.schedule["interval"] == 3
        assert template.schedule["frequency"] == "WEEKLY"

    def test_update_mode_clears_m2m_when_column_empty(
        self, base_context, update_context, domain_folder
    ):
        asset = Asset.objects.create(name="Server", folder=domain_folder)
        _run(base_context, [dict(self.RECORD, assets="Server")])
        template = TaskTemplate.objects.get(name="Recurring scan")
        assert list(template.assets.all()) == [asset]

        result = _run(update_context, [dict(self.RECORD, assets="")])
        assert result.updated == 1, result.to_dict()
        assert template.assets.count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# LoadFileView integration — multi-sheet Excel and CSV
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTaskTemplateEndpoint:
    def test_multi_sheet_creates_templates_and_past_nodes(
        self, api_client, domain_folder, all_accessible
    ):
        excel = make_excel_file(
            {
                "Summary": [
                    {
                        "name": "Recurring scan",
                        "is_recurrent": "Yes",
                        "schedule_frequency": "WEEKLY",
                        "schedule_interval": "1",
                    }
                ],
                "1-Recurring scan": [
                    {"due_date": "2020-01-06", "status": "completed"},
                    {"due_date": "2099-01-06", "status": "pending"},  # future
                ],
            }
        )
        resp = _post(api_client, excel.read(), "tasks.xlsx", domain_folder.id)
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert results["templates"]["created"] == 1, results
        assert results["task_nodes"]["created"] == 1, results

        template = TaskTemplate.objects.get(name="Recurring scan")
        nodes = TaskNode.objects.filter(task_template=template)
        assert nodes.count() == 1
        assert str(nodes.first().due_date) == "2020-01-06"
        assert nodes.first().status == "completed"

    def test_roundtrip_non_recurrent_stop_mode_has_no_conflict(
        self, api_client, domain_folder, all_accessible
    ):
        # Export-like workbook: non-recurrent template + its single past node.
        # The serializer auto-creates the node from task_date; the node sheet
        # must update it, not raise "already exists" in default STOP mode.
        excel = make_excel_file(
            {
                "Summary": [
                    {
                        "name": "One-shot audit",
                        "is_recurrent": "No",
                        "task_date": "2020-02-01",
                        "status": "completed",
                    }
                ],
                "1-One-shot audit": [
                    {
                        "due_date": "2020-02-01",
                        "status": "completed",
                        "observation": "done",
                    }
                ],
            }
        )
        resp = _post(api_client, excel.read(), "tasks.xlsx", domain_folder.id)
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert results["templates"]["created"] == 1, results
        assert results["task_nodes"]["errors"] == [], results
        assert results["task_nodes"]["stopped"] is False
        assert results["task_nodes"]["updated"] == 1

        template = TaskTemplate.objects.get(name="One-shot audit")
        nodes = TaskNode.objects.filter(task_template=template)
        assert nodes.count() == 1
        assert nodes.first().observation == "done"

    def test_legacy_sheet_numbering_matched_by_name(
        self, api_client, domain_folder, all_accessible
    ):
        # Files exported before counters were aligned with summary rows number
        # only templates that had nodes: with Alpha node-less, Beta's sheet is
        # "1-Beta" while Beta is summary row 2. Nodes must land on Beta.
        excel = make_excel_file(
            {
                "Summary": [
                    {
                        "name": "Alpha",
                        "is_recurrent": "Yes",
                        "schedule_frequency": "MONTHLY",
                        "schedule_interval": "1",
                    },
                    {
                        "name": "Beta",
                        "is_recurrent": "Yes",
                        "schedule_frequency": "MONTHLY",
                        "schedule_interval": "1",
                    },
                ],
                "1-Beta": [{"due_date": "2020-03-02", "status": "completed"}],
            }
        )
        resp = _post(api_client, excel.read(), "tasks.xlsx", domain_folder.id)
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert results["task_nodes"]["created"] == 1, results
        assert results["task_nodes"].get("warnings"), results

        alpha = TaskTemplate.objects.get(name="Alpha")
        beta = TaskTemplate.objects.get(name="Beta")
        assert TaskNode.objects.filter(task_template=beta).count() == 1
        assert TaskNode.objects.filter(task_template=alpha).count() == 0

    def test_csv_with_bom_and_semicolon_delimiter(
        self, api_client, domain_folder, all_accessible
    ):
        csv_bytes = (
            "\ufeffref_id;name;is_recurrent;schedule_frequency;schedule_interval\n"
            "TT-1;Bom template;Yes;MONTHLY;1\n"
        ).encode("utf-8")
        resp = _post(api_client, csv_bytes, "tasks.csv", domain_folder.id)
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1

        # ref_id survives only if the BOM was stripped from the first header
        template = TaskTemplate.objects.get(name="Bom template")
        assert template.ref_id == "TT-1"
