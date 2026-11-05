"""Metrics through the mapped import: instances of library definitions, then
their samples in the same run, numeric and qualitative."""

import json
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from metrology.models import CustomMetricSample, MetricDefinition, MetricInstance

SAMPLES = Path(__file__).parent / "samples"
IMPORT_URL = "/api/data-wizard/mapping/import/"
KPI_FILE = "11_kpi_monthly_pack.xlsx"


@pytest.fixture
def definitions(root_folder):
    MetricDefinition.objects.create(
        ref_id="VULN-01",
        name="Open Critical/High Vulnerabilities",
        category=MetricDefinition.Category.QUANTITATIVE,
        folder=root_folder,
    )
    MetricDefinition.objects.create(
        ref_id="GOV-02",
        name="Security Program Maturity",
        category=MetricDefinition.Category.QUALITATIVE,
        choices_definition=[
            {"name": "Initial"},
            {"name": "Developing"},
            {"name": "Defined"},
            {"name": "Managed"},
        ],
        folder=root_folder,
    )


INSTANCES = {
    "model_type": "MetricInstance",
    "sheets": [
        {
            "source": "KPIs",
            "target": "Metric instances",
            "columns": {
                "KPI code": "ref_id",
                "KPI": "name",
                "What it measures": "description",
                "Metric": "metric_definition",
                "Target": "target_value",
                "Frequency": "collection_frequency",
            },
            "values": {"Frequency": {"Monthly": "monthly", "Quarterly": "quarterly"}},
        }
    ],
}
SAMPLES_STEP = {
    "model_type": "CustomMetricSample",
    "sheets": [
        {
            "source": "Monthly values",
            "target": "Samples",
            "columns": {
                "KPI code": "metric_instance",
                "Month": "timestamp",
                "Value": "value",
                "Comment": "observation",
            },
        }
    ],
}


def _import(client, folder, steps, dry_run=False):
    return client.post(
        IMPORT_URL,
        {
            "file": SimpleUploadedFile(KPI_FILE, (SAMPLES / KPI_FILE).read_bytes()),
            "mapping": json.dumps({"steps": steps}),
            "options": json.dumps({"folder_id": str(folder.id), "on_conflict": "skip"}),
            "dry_run": str(dry_run).lower(),
        },
        format="multipart",
    )


@pytest.mark.django_db
class TestMetrics:
    def test_instances_then_samples_in_one_run(
        self, api_client, domain_folder, definitions, all_accessible
    ):
        resp = _import(api_client, domain_folder, [INSTANCES, SAMPLES_STEP])
        assert resp.status_code == 200, resp.json()
        vuln = MetricInstance.objects.get(ref_id="KPI-VULN")
        assert vuln.metric_definition.ref_id == "VULN-01"
        assert vuln.collection_frequency == "monthly"
        assert vuln.target_value == 0
        assert vuln.folder == domain_folder
        values = list(
            CustomMetricSample.objects.filter(metric_instance=vuln)
            .order_by("timestamp")
            .values_list("value", flat=True)
        )
        assert [v["result"] for v in values] == [18, 11, 7]

    def test_qualitative_levels_by_name(
        self, api_client, domain_folder, definitions, all_accessible
    ):
        resp = _import(api_client, domain_folder, [INSTANCES, SAMPLES_STEP])
        maturity = MetricInstance.objects.get(ref_id="KPI-MAT")
        levels = sorted(
            s.value["choice_index"]
            for s in CustomMetricSample.objects.filter(metric_instance=maturity)
        )
        assert levels == [2, 3]  # Developing, Defined; "Excelent" is refused
        errors = " ".join(
            e["error"] for e in resp.json()["steps"][1]["results"]["errors"]
        )
        assert "'Excelent' is none of initial, developing, defined, managed" in errors
        assert "no metric instance 'KPI-LOST'" in errors

    def test_unknown_definition_is_reported(
        self, api_client, domain_folder, all_accessible
    ):
        resp = _import(api_client, domain_folder, [INSTANCES])
        errors = [e["error"] for e in resp.json()["steps"][0]["results"]["errors"]]
        assert errors[0] == "metric_definition: no metric definition 'VULN-01'"

    def test_dry_run_writes_nothing(
        self, api_client, domain_folder, definitions, all_accessible
    ):
        resp = _import(api_client, domain_folder, [INSTANCES, SAMPLES_STEP], True)
        assert resp.json()["steps"][1]["results"]["created"] == 5
        assert not MetricInstance.objects.exists()
        assert not CustomMetricSample.objects.exists()

    def test_template_download(self, api_client):
        for model_type in ("MetricInstance", "CustomMetricSample"):
            resp = api_client.get(f"/api/data-wizard/templates/{model_type}/")
            assert resp.status_code == 200
