"""Edge cases from review: stops inside multi-sheet importers, CSV read like a
sheet, saved header rows, malformed input, odd timestamps and metric names
repeated across domains."""

import io
import json
from datetime import date

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import Asset, TaskTemplate
from data_wizard.mapping import _stopped
from data_wizard.models import ImportMapping
from iam.models import Folder
from metrology.models import CustomMetricSample, MetricDefinition, MetricInstance

ANALYZE_URL = "/api/data-wizard/mapping/analyze/"
IMPORT_URL = "/api/data-wizard/mapping/import/"
MAPPINGS_URL = "/api/data-wizard/mappings/"


def _xlsx(sheets: dict[str, list[list]]) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for title, rows in sheets.items():
        ws = wb.create_sheet(title)
        for row in rows:
            ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _post(client, url, name, data, **fields):
    return client.post(
        url,
        {
            "file": SimpleUploadedFile(name, data),
            **{
                k: v if isinstance(v, str) else json.dumps(v) for k, v in fields.items()
            },
        },
        format="multipart",
    )


def test_stop_is_seen_inside_multi_sheet_results():
    assert _stopped({"templates": {"stopped": True}, "task_nodes": {}})
    assert _stopped({"stopped": True})
    assert not _stopped({"templates": {"stopped": False}})
    assert not _stopped(None)


@pytest.mark.django_db
def test_a_stopped_task_step_halts_the_next_step(
    api_client, domain_folder, all_accessible
):
    TaskTemplate.objects.create(name="Access review", folder=domain_folder)
    data = _xlsx(
        {"Tasks": [["Name"], ["Access review"]], "Assets": [["Name"], ["Laptop"]]}
    )
    steps = [
        {
            "model_type": "Asset",
            "sheets": [
                {"source": "Assets", "target": "Sheet1", "columns": {"Name": "name"}}
            ],
        },
        {
            "model_type": "TaskTemplate",
            "sheets": [
                {"source": "Tasks", "target": "Summary", "columns": {"Name": "name"}}
            ],
        },
    ]
    # Tasks first: the order the client sends is the order run.
    resp = _post(
        api_client,
        IMPORT_URL,
        "two.xlsx",
        data,
        mapping={"steps": steps[::-1]},
        options={"folder_id": str(domain_folder.id), "on_conflict": "stop"},
    )
    assert resp.status_code == 200, resp.json()
    assert [s["model_type"] for s in resp.json()["steps"]] == ["TaskTemplate"]
    assert not Asset.objects.filter(name="Laptop").exists()


CSV_WITH_TITLE = (
    b"Vendor findings export,,\n"
    b",,\n"
    b"Asset ID,Name,Description\n"
    b"007,Laptop,Field laptop\n"
    b"1.10,Badge reader,Lobby\n"
)


@pytest.mark.django_db
class TestCsvReadLikeASheet:
    def test_title_line_is_skipped_and_codes_stay_text(self, api_client):
        resp = _post(api_client, ANALYZE_URL, "assets.csv", CSV_WITH_TITLE)
        sheet = resp.json()["sheets"][0]
        assert sheet["header_row"] == 3
        codes = next(c for c in sheet["columns"] if c["header"] == "Asset ID")
        assert codes["samples"][:2] == ["007", "1.10"]

    def test_imported_ref_ids_keep_their_zeros(
        self, api_client, domain_folder, all_accessible
    ):
        step = {
            "model_type": "Asset",
            "sheets": [
                {
                    "source": "CSV",
                    "target": "Sheet1",
                    "header_row": 3,
                    "columns": {"Asset ID": "ref_id", "Name": "name"},
                }
            ],
        }
        resp = _post(
            api_client,
            IMPORT_URL,
            "assets.csv",
            CSV_WITH_TITLE,
            mapping={"steps": [step]},
            options={"folder_id": str(domain_folder.id)},
        )
        assert resp.status_code == 200, resp.json()
        assert sorted(Asset.objects.values_list("ref_id", flat=True)) == [
            "007",
            "1.10",
        ]


@pytest.mark.django_db
def test_saved_mapping_finds_its_hand_set_header_row(api_client, root_folder):
    banner = ["Asset report", "Owner: IT", "Period: Q3", "Draft", "v2", "Internal"]
    data = _xlsx({"Assets": [banner, [], ["ID", "Name", "Notes"], ["A1", "NAS", ""]]})
    ImportMapping.objects.create(
        name="Asset report",
        folder=root_folder,
        sheets=[
            {
                "source": "Assets",
                "headers": ["ID", "Name", "Notes"],
                "header_row": 3,
                "model_type": "Asset",
                "target": "Sheet1",
                "columns": {"ID": "ref_id", "Name": "name"},
            }
        ],
    )
    sheet = _post(api_client, ANALYZE_URL, "report.xlsx", data).json()["sheets"][0]
    assert sheet["header_row"] == 3
    assert sheet["saved_mapping"]["name"] == "Asset report"


@pytest.mark.django_db
class TestBadInputIsA400:
    DATA = _xlsx({"Assets": [["Name"], ["NAS"]]})

    def test_header_row_past_the_end(self, api_client, domain_folder):
        resp = _post(
            api_client,
            ANALYZE_URL,
            "a.xlsx",
            self.DATA,
            overrides={"Assets": {"header_row": 50}},
        )
        assert resp.status_code == 400
        step = {
            "model_type": "Asset",
            "sheets": [
                {
                    "source": "Assets",
                    "target": "Sheet1",
                    "header_row": 50,
                    "columns": {"Name": "name"},
                }
            ],
        }
        resp = _post(
            api_client,
            IMPORT_URL,
            "a.xlsx",
            self.DATA,
            mapping={"steps": [step]},
            options={"folder_id": str(domain_folder.id)},
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        "fields",
        [
            {"mapping": {"steps": ["x"]}},
            {"mapping": []},
            {"mapping": {"steps": [{"model_type": "Asset", "sheets": ["a"]}]}},
            {
                "mapping": {
                    "steps": [{"model_type": "Asset", "sheets": [], "options": []}]
                }
            },
            {"mapping": {"steps": []}, "options": []},
        ],
    )
    def test_malformed_mapping(self, api_client, fields):
        resp = _post(api_client, IMPORT_URL, "a.xlsx", self.DATA, **fields)
        assert resp.status_code == 400

    def test_malformed_overrides(self, api_client):
        for overrides in ([], {"Assets": "x"}):
            resp = _post(
                api_client, ANALYZE_URL, "a.xlsx", self.DATA, overrides=overrides
            )
            assert resp.status_code == 400

    def test_malformed_saved_sheets(self, api_client, root_folder):
        resp = api_client.post(
            MAPPINGS_URL,
            {"name": "Bad", "folder": str(root_folder.id), "sheets": ["a"]},
            format="json",
        )
        assert resp.status_code == 400

    def test_bad_saved_mapping_ids_fail_before_any_write(
        self, api_client, domain_folder, all_accessible
    ):
        step = {
            "model_type": "Asset",
            "sheets": [
                {"source": "Assets", "target": "Sheet1", "columns": {"Name": "name"}}
            ],
        }
        resp = _post(
            api_client,
            IMPORT_URL,
            "a.xlsx",
            self.DATA,
            mapping={"steps": [step]},
            options={"folder_id": str(domain_folder.id), "saved_mapping_ids": "abc"},
        )
        assert resp.status_code == 400
        assert not Asset.objects.exists()


@pytest.fixture
def two_domains(root_folder, domain_folder):
    other = Folder.objects.create(
        name="Other domain",
        parent_folder=root_folder,
        content_type=Folder.ContentType.DOMAIN,
    )
    definition = MetricDefinition.objects.create(
        ref_id="PATCH",
        name="Patch coverage",
        category=MetricDefinition.Category.QUANTITATIVE,
        folder=root_folder,
    )
    for folder in (domain_folder, other):
        MetricInstance.objects.create(
            name="Patch coverage", metric_definition=definition, folder=folder
        )
    return domain_folder, other


def _samples(client, folder, values):
    step = {
        "model_type": "CustomMetricSample",
        "sheets": [
            {
                "source": "Values",
                "target": "Samples",
                "columns": {
                    "KPI": "metric_instance",
                    "When": "timestamp",
                    "Value": "value",
                },
            }
        ],
    }
    data = _xlsx({"Values": [["KPI", "When", "Value"], *values]})
    return _post(
        client,
        IMPORT_URL,
        "kpi.xlsx",
        data,
        mapping={"steps": [step]},
        options={
            "folder_id": str(folder.id) if folder else "",
            "on_conflict": "skip",
        },
    )


@pytest.mark.django_db
class TestMetricSamples:
    def test_a_number_as_timestamp_fails_only_its_row(
        self, api_client, two_domains, all_accessible
    ):
        resp = _samples(
            api_client,
            two_domains[0],
            [["Patch coverage", 45000, 91], ["Patch coverage", date(2026, 9, 30), 93]],
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["steps"][0]["results"]
        assert results["created"] == 1
        assert "'45000' is not a date" in json.dumps(results["errors"])

    def test_same_name_in_two_domains_resolves_in_the_import_domain(
        self, api_client, two_domains, all_accessible
    ):
        _, other = two_domains
        _samples(api_client, other, [["Patch coverage", date(2026, 9, 30), 93]])
        sample = CustomMetricSample.objects.get()
        assert sample.metric_instance.folder == other

    def test_same_name_without_a_domain_is_reported(
        self, api_client, two_domains, all_accessible
    ):
        resp = _samples(api_client, None, [["Patch coverage", date(2026, 9, 30), 93]])
        errors = json.dumps(resp.json()["steps"][0]["results"]["errors"])
        assert "several metric instances are named 'Patch coverage'" in errors
        assert not CustomMetricSample.objects.exists()


@pytest.mark.django_db
def test_refusals_name_the_code_not_the_input(api_client, domain_folder):
    step = {
        "model_type": "Asset",
        "sheets": [
            {"source": "Assets", "target": "Sheet1", "columns": {"Name": "<secret>"}}
        ],
    }
    resp = _post(
        api_client,
        IMPORT_URL,
        "a.xlsx",
        _xlsx({"Assets": [["Name"], ["NAS"]]}),
        mapping={"steps": [step]},
        options={"folder_id": str(domain_folder.id)},
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "invalidMapping", "detail": "UnknownColumns"}


@pytest.mark.django_db
def test_a_new_audit_without_framework_is_a_row_error(
    api_client, domain_folder, all_accessible
):
    step = {
        "model_type": "ComplianceAssessment",
        "options": {"container_name": "No framework"},
        "sheets": [
            {
                "source": "Answers",
                "target": "Requirements",
                "columns": {"Ref": "ref_id", "Result": "compliance_result"},
            }
        ],
    }
    resp = _post(
        api_client,
        IMPORT_URL,
        "audit.xlsx",
        _xlsx({"Answers": [["Ref", "Result"], ["A.5.1", "compliant"]]}),
        mapping={"steps": [step]},
        options={"folder_id": str(domain_folder.id)},
    )
    assert resp.status_code == 200
    results = resp.json()["steps"][0]["results"]
    assert results["failed"] == 1
    assert "Failed to create compliance assessment" in json.dumps(results["errors"])
