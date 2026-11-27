"""What the mapped import makes of our own templates and of the exports it
reads whole (EGERIE, ARM, EBIOS RM, CyFun)."""

import io
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import RiskMatrix, TaskNode, TaskTemplate
from data_wizard import mapping
from data_wizard.tests.test_arm_helpers import (
    EN_SHEETS,
    PER_TABLE_EXPORTS,
    build_archive,
    build_workbook,
)
from data_wizard.tests.test_cyfun import filled_2023_tool
from data_wizard.tests.test_templates import ebios_4x4_matrix  # noqa: F401 (fixture)
from data_wizard.tests.test_utils import MINIMAL_EGERIE_XML
from data_wizard.views import IMPORT_TEMPLATES, IMPORT_TEMPLATES_DIR, ModelType
from ebios_rm.models import EbiosRMStudy

ANALYZE_URL = "/api/data-wizard/mapping/analyze/"
IMPORT_URL = "/api/data-wizard/mapping/import/"
MAPPED_TEMPLATES = sorted(IMPORT_TEMPLATES.keys() & mapping.TEMPLATE_ROW_MODELS.keys())


def _analyse(model_type: ModelType) -> list[dict]:
    content = (IMPORT_TEMPLATES_DIR / IMPORT_TEMPLATES[model_type]).read_bytes()
    return mapping.analyze(io.BytesIO(content), set())["sheets"]


@pytest.mark.django_db
def test_schema_lists_every_downloadable_template(api_client):
    resp = api_client.get("/api/data-wizard/mapping/schema/")
    assert set(resp.json()["templates"]) == {t.value for t in IMPORT_TEMPLATES}
    for model_type in resp.json()["templates"]:
        assert (
            api_client.get(f"/api/data-wizard/templates/{model_type}/").status_code
            == 200
        ), model_type


@pytest.mark.django_db
@pytest.mark.parametrize("model_type", MAPPED_TEMPLATES)
def test_each_template_is_recognised_column_for_column(model_type):
    for sheet in _analyse(model_type):
        if sheet.get("companion"):
            continue
        assert sheet["target"]["model_type"] == model_type.value, sheet["name"]
        assert sheet["target"]["sheet"] == sheet["name"]
        columns = sheet["mapping"]["columns"]
        assert {h: c["key"] for h, c in columns.items()} == {
            c["header"]: c["header"].strip().lower() for c in sheet["columns"]
        }


@pytest.mark.django_db
def test_template_side_sheets_are_not_imported_as_records():
    notes = next(s for s in _analyse(ModelType.FOLDER) if s["name"] == "Notes")
    assert notes["companion"] == "notes"
    sheets = _analyse(ModelType.TASK_TEMPLATE)
    assert {s["name"]: s.get("companion") for s in sheets} == {
        "Summary": None,
        "1-task": "occurrences",
        "2-Security awareness training": "occurrences",
        "3-Internal ISMS audit": "occurrences",
        "4-task": "occurrences",
    }


@pytest.mark.django_db
def test_tasks_template_imports_like_the_direct_importer(
    api_client, domain_folder, all_accessible
):
    content = (IMPORT_TEMPLATES_DIR / "tasks_template.xlsx").read_bytes()
    summary = next(
        s for s in _analyse(ModelType.TASK_TEMPLATE) if s["name"] == "Summary"
    )
    step = {
        "model_type": "TaskTemplate",
        "sheets": [
            {
                "source": "Summary",
                "target": "Summary",
                "header_row": 1,
                "columns": {
                    h: c["key"] for h, c in summary["mapping"]["columns"].items()
                },
            }
        ],
    }
    resp = api_client.post(
        IMPORT_URL,
        {
            "file": SimpleUploadedFile("tasks_template.xlsx", content),
            "mapping": json.dumps({"steps": [step]}),
            "options": json.dumps({"folder_id": str(domain_folder.id)}),
        },
        format="multipart",
    )
    assert resp.status_code == 200, resp.json()
    results = resp.json()["steps"][0]["results"]
    assert results["templates"]["created"] == 8
    assert results["task_nodes"]["failed"] == 0
    assert TaskTemplate.objects.count() == 8
    nodes = TaskNode.objects.count()
    # The direct importer, on a clean slate, reads as many occurrences.
    TaskTemplate.objects.all().delete()
    direct = api_client.post(
        "/api/data-wizard/load-file/",
        data=content,
        content_type="application/octet-stream",
        HTTP_X_MODEL_TYPE="TaskTemplate",
        HTTP_X_FOLDER_ID=str(domain_folder.id),
        HTTP_CONTENT_DISPOSITION="attachment; filename=tasks_template.xlsx",
    ).json()["results"]
    assert results["task_nodes"] == direct["task_nodes"]
    assert TaskNode.objects.count() == nodes


class TestRecognisedFormats:
    @pytest.mark.parametrize(
        "content,model_type",
        [
            (MINIMAL_EGERIE_XML, ModelType.EBIOS_RM_STUDY_EGERIE_XML),
            (build_workbook(EN_SHEETS), ModelType.EBIOS_RM_STUDY_ARM),
            (build_archive(PER_TABLE_EXPORTS), ModelType.EBIOS_RM_STUDY_ARM),
            (filled_2023_tool(), ModelType.CYFUN_ASSESSMENT),
            (
                build_workbook(
                    {
                        "1.1 Study": [["name"], ["S"]],
                        "1.2 Assets": [["name"], ["A"]],
                        "2.1 RoTo": [["risk_origin"], ["X"]],
                    }
                ),
                ModelType.EBIOS_RM_STUDY_EXCEL,
            ),
        ],
    )
    def test_exports_are_recognised(self, content, model_type):
        assert mapping.recognise_format(content) == model_type

    @pytest.mark.django_db
    @pytest.mark.parametrize("model_type", MAPPED_TEMPLATES)
    def test_templates_are_mapped_not_read_whole(self, model_type):
        content = (IMPORT_TEMPLATES_DIR / IMPORT_TEMPLATES[model_type]).read_bytes()
        assert mapping.recognise_format(content) is None

    def test_other_files_are_not(self):
        assert mapping.recognise_format(b"<?xml version='1.0'?><a/>") is None
        assert mapping.recognise_format(build_archive({"x.xlsx": [["a"]]})) is None

    def test_analysis_names_the_format(self, api_client):
        resp = api_client.post(
            ANALYZE_URL,
            {"file": SimpleUploadedFile("study.xml", MINIMAL_EGERIE_XML)},
            format="multipart",
        )
        assert resp.json() == {"format": "EbiosRMStudyEgerieXML", "sheets": []}

    def test_an_unknown_xml_is_refused(self, api_client):
        resp = api_client.post(
            ANALYZE_URL,
            {"file": SimpleUploadedFile("other.xml", b"<?xml version='1.0'?><a/>")},
            format="multipart",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "UnrecognisedFile"

    def test_a_workbook_can_still_be_mapped(self, api_client):
        resp = api_client.post(
            ANALYZE_URL,
            {
                "file": SimpleUploadedFile("arm.xlsx", build_workbook(EN_SHEETS)),
                "detect_format": "false",
            },
            format="multipart",
        )
        assert resp.status_code == 200
        assert resp.json()["sheets"]

    @pytest.mark.usefixtures("ebios_4x4_matrix")
    @pytest.mark.parametrize("dry_run", [True, False])
    def test_whole_file_import(self, api_client, domain_folder, dry_run):
        matrix = RiskMatrix.objects.get(ref_id="risk-matrix-4x4-ebios-rm")
        resp = api_client.post(
            IMPORT_URL,
            {
                "file": SimpleUploadedFile("study.xml", MINIMAL_EGERIE_XML),
                "mapping": json.dumps(
                    {"steps": [{"model_type": "EbiosRMStudyEgerieXML"}]}
                ),
                "options": json.dumps(
                    {
                        "folder_id": str(domain_folder.id),
                        "matrix_id": str(matrix.id),
                    }
                ),
                "dry_run": str(dry_run).lower(),
            },
            format="multipart",
        )
        assert resp.status_code == 200, resp.json()
        [step] = resp.json()["steps"]
        assert step["status"] == 200
        assert EbiosRMStudy.objects.exists() is not dry_run
