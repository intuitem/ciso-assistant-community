"""Power BI connector contract tests.

The connector at automation/powerbi/connector/CisoAssistant.pq hard-codes
column names, JSON paths and types (v1 decision). This test loads the
shared contract (automation/powerbi/contract.json) and asserts that every
path the connector consumes is present in the live serializer output with
a compatible JSON type, so a serializer refactor cannot silently break
Power BI refreshes.
"""

import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.utils import timezone

CONTRACT_PATH = (
    Path(__file__).resolve().parents[3] / "automation" / "powerbi" / "contract.json"
)
CONTRACT = json.loads(CONTRACT_PATH.read_text())

_MISSING = object()

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")
DECIMAL_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _walk(value, path):
    for key in path:
        if value is None:
            return None
        if not isinstance(value, dict):
            return _MISSING
        if key not in value:
            return _MISSING
        value = value[key]
    return value


def _check_type(value, expected, ctx):
    if value is None:
        return
    if expected == "string":
        assert isinstance(value, str), ctx
    elif expected == "integer":
        assert isinstance(value, int) and not isinstance(value, bool), ctx
    elif expected == "number":
        assert (isinstance(value, (int, float)) and not isinstance(value, bool)) or (
            isinstance(value, str) and DECIMAL_RE.match(value)
        ), ctx
    elif expected == "boolean":
        assert isinstance(value, bool), ctx
    elif expected == "date":
        assert isinstance(value, str) and DATE_RE.match(value), ctx
    elif expected == "datetime":
        assert isinstance(value, str) and DATETIME_RE.match(value), ctx
    elif expected == "breadcrumb":
        assert isinstance(value, list), ctx
        for crumb in value:
            assert isinstance(crumb, dict) and "str" in crumb, ctx
    elif expected == "stringlist":
        assert isinstance(value, list), ctx
    else:
        raise AssertionError(f"unknown contract type {expected} ({ctx})")


@pytest.fixture
def bi_dataset(db):
    from test_fixtures import RISK_MATRIX_JSON_DEFINITION

    from core.models import (
        AppliedControl,
        Asset,
        ComplianceAssessment,
        Evidence,
        EvidenceRevision,
        FilteringLabel,
        Finding,
        FindingsAssessment,
        Framework,
        Incident,
        LoadedLibrary,
        Perimeter,
        ReferenceControl,
        RequirementAssessment,
        RequirementNode,
        RiskAssessment,
        RiskMatrix,
        RiskScenario,
        SecurityException,
        Threat,
        Vulnerability,
    )
    from iam.models import Folder

    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        name="BI Contract Domain",
        parent_folder=root,
        content_type=Folder.ContentType.DOMAIN,
    )
    perimeter = Perimeter.objects.create(name="BI Perimeter", folder=domain)
    library = LoadedLibrary.objects.create(
        name="BI Contract Library",
        urn="urn:test:risk:library:powerbi-contract",
        locale="en",
        default_locale=True,
        version=1,
        objects_meta={},
        folder=root,
    )
    framework = Framework.objects.create(
        name="BI Contract Framework",
        urn="urn:test:risk:framework:powerbi-contract",
        ref_id="BI-FWK",
        provider="test",
        library=library,
        folder=root,
    )
    requirement = RequirementNode.objects.create(
        name="BI Requirement",
        urn="urn:test:req_node:powerbi-contract:1",
        ref_id="R.1",
        framework=framework,
        folder=root,
        assessable=True,
        order_id=1,
        implementation_groups=["A"],
    )
    reference_control = ReferenceControl.objects.create(
        name="BI Reference Control",
        urn="urn:test:reference_control:powerbi-contract",
        library=library,
        folder=root,
    )
    compliance_assessment = ComplianceAssessment.objects.create(
        name="BI Audit",
        framework=framework,
        folder=domain,
        perimeter=perimeter,
        ref_id="AUD-1",
        eta=date.today(),
        due_date=date.today() + timedelta(days=30),
        observation="observation",
        # Score fields are HIDDEN by default (core.utils.DEFAULT_VISIBILITY)
        # and stripped from the payload. Expose them so the contract can
        # assert their shape; audits that hide them simply yield nulls in
        # Power BI.
        field_visibility={
            "score": {"auditor": "edit", "respondent": "hidden"},
            "is_scored": {"auditor": "edit", "respondent": "hidden"},
            "documentation_score": {"auditor": "edit", "respondent": "hidden"},
        },
    )
    requirement_assessment = RequirementAssessment.objects.create(
        compliance_assessment=compliance_assessment,
        requirement=requirement,
        folder=domain,
        eta=date.today(),
        due_date=date.today() + timedelta(days=30),
        is_scored=True,
        score=2,
        documentation_score=1,
        observation="observation",
    )
    applied_control = AppliedControl.objects.create(
        name="BI Control",
        folder=domain,
        ref_id="AC-1",
        reference_control=reference_control,
        start_date=date.today(),
        eta=date.today() + timedelta(days=10),
        expiry_date=date.today() + timedelta(days=100),
        link="https://example.com/control",
        observation="observation",
    )
    evidence = Evidence.objects.create(
        name="BI Evidence", folder=domain, expiry_date=date.today()
    )
    EvidenceRevision.objects.create(
        evidence=evidence,
        folder=domain,
        version=1,
        link="https://example.com/evidence",
    )
    findings_assessment = FindingsAssessment.objects.create(
        name="BI Findings Assessment", folder=domain, perimeter=perimeter
    )
    asset = Asset.objects.create(name="BI Asset", folder=domain)
    finding = Finding.objects.create(
        name="BI Finding",
        folder=domain,
        ref_id="F-1",
        findings_assessment=findings_assessment,
        eta=date.today(),
        due_date=date.today() + timedelta(days=15),
        observation="observation",
    )
    incident = Incident.objects.create(
        name="BI Incident",
        folder=domain,
        ref_id="INC-1",
        reported_at=timezone.now(),
        link="https://example.com/incident",
    )

    threat = Threat.objects.create(
        name="BI Threat",
        urn="urn:test:threat:powerbi-contract",
        ref_id="T.1",
        provider="test",
        library=library,
        folder=root,
    )
    risk_matrix = RiskMatrix.objects.create(
        name="BI Matrix",
        folder=domain,
        json_definition=RISK_MATRIX_JSON_DEFINITION,
    )
    risk_assessment = RiskAssessment.objects.create(
        name="BI Risk Assessment",
        ref_id="RA-1",
        version="1.0",
        folder=domain,
        perimeter=perimeter,
        risk_matrix=risk_matrix,
        eta=date.today(),
        due_date=date.today() + timedelta(days=30),
    )
    risk_scenario = RiskScenario.objects.create(
        name="BI Risk Scenario",
        ref_id="R.1",
        risk_assessment=risk_assessment,
        current_proba=0,
        current_impact=0,
        current_level=0,
        residual_proba=0,
        residual_impact=0,
        residual_level=0,
    )
    vulnerability = Vulnerability.objects.create(
        name="BI Vulnerability",
        ref_id="V-1",
        folder=domain,
        detected_at=date.today() - timedelta(days=10),
        published_date=date.today() - timedelta(days=20),
        eta=date.today() + timedelta(days=10),
        due_date=date.today() + timedelta(days=30),
    )
    security_exception = SecurityException.objects.create(
        name="BI Security Exception",
        ref_id="SE-1",
        folder=domain,
        expiration_date=date.today() + timedelta(days=90),
        link="https://example.com/exception",
        observation="observation",
    )
    label = FilteringLabel.objects.create(label="bi-contract", folder=domain)
    parent_asset = Asset.objects.create(name="BI Parent Asset", folder=domain)
    asset.parent_assets.add(parent_asset)

    requirement_assessment.applied_controls.add(applied_control)
    requirement_assessment.evidences.add(evidence)
    applied_control.evidences.add(evidence)
    applied_control.filtering_labels.add(label)
    finding.applied_controls.add(applied_control)
    finding.evidences.add(evidence)
    finding.vulnerabilities.add(vulnerability)
    finding.filtering_labels.add(label)
    incident.applied_controls.add(applied_control)
    incident.assets.add(asset)
    incident.threats.add(threat)
    incident.filtering_labels.add(label)
    risk_scenario.assets.add(asset)
    risk_scenario.threats.add(threat)
    risk_scenario.applied_controls.add(applied_control)
    risk_scenario.vulnerabilities.add(vulnerability)
    risk_scenario.filtering_labels.add(label)
    vulnerability.assets.add(asset)
    vulnerability.applied_controls.add(applied_control)
    vulnerability.filtering_labels.add(label)

    return {
        "requirement-assessments": requirement_assessment,
        "applied-controls": applied_control,
        "findings": finding,
        "evidences": evidence,
        "incidents": incident,
        "compliance-assessments": compliance_assessment,
        "frameworks": framework,
        "requirement-nodes": requirement,
        "folders": domain,
        "risk-scenarios": risk_scenario,
        "vulnerabilities": vulnerability,
        "security-exceptions": security_exception,
        "assets": asset,
        "risk-assessments": risk_assessment,
        "perimeters": perimeter,
        "threats": threat,
        "reference-controls": reference_control,
        "findings-assessments": findings_assessment,
        "filtering-labels": label,
    }


def _get_row(client, endpoint, obj_id):
    response = client.get(f"/api/{endpoint}/", {"limit": 1000})
    assert response.status_code == 200, f"{endpoint}: {response.status_code}"
    payload = response.json()
    assert "results" in payload and "count" in payload, (
        f"{endpoint}: pagination envelope missing"
    )
    rows = [r for r in payload["results"] if r.get("id") == str(obj_id)]
    assert rows, f"{endpoint}: seeded object not in list response"
    return rows[0]


@pytest.mark.django_db
def test_powerbi_table_contract(authenticated_client, bi_dataset):
    for table_name, table in CONTRACT["tables"].items():
        endpoint = table["endpoint"]
        row = _get_row(authenticated_client, endpoint, bi_dataset[endpoint].id)
        for column in table["columns"]:
            ctx = f"{table_name}.{column['name']} (path {column['path']})"
            value = _walk(row, column["path"])
            assert value is not _MISSING, f"missing: {ctx}"
            _check_type(value, column["type"], ctx)


@pytest.mark.django_db
def test_powerbi_bridge_contract(authenticated_client, bi_dataset):
    for bridge in CONTRACT["bridges"]:
        endpoint = bridge["endpoint"]
        row = _get_row(authenticated_client, endpoint, bi_dataset[endpoint].id)
        ctx = f"bridge {bridge['name']}"
        children = row.get(bridge["list_field"], _MISSING)
        assert children is not _MISSING, f"missing list field: {ctx}"
        assert isinstance(children, list) and children, f"empty list field: {ctx}"
        for child in children:
            # The connector accepts both M2M shapes: {id, str} records
            # (FieldsRelatedField) or plain id strings (PrimaryKeyRelatedField)
            assert (isinstance(child, dict) and "id" in child) or isinstance(
                child, str
            ), ctx


@pytest.mark.django_db
def test_powerbi_incremental_refresh_params(authenticated_client, bi_dataset):
    for table in CONTRACT["tables"].values():
        endpoint = table["endpoint"]
        if endpoint not in (
            "requirement-assessments",
            "applied-controls",
            "findings",
            "evidences",
            "incidents",
            "risk-scenarios",
            "vulnerabilities",
            "security-exceptions",
            "assets",
        ):
            continue
        past = authenticated_client.get(
            f"/api/{endpoint}/",
            {"limit": 10, "updated_at__gte": "2000-01-01T00:00:00Z"},
        )
        assert past.status_code == 200, endpoint
        assert past.json()["count"] >= 1, f"{endpoint}: expected rows since 2000"

        future = authenticated_client.get(
            f"/api/{endpoint}/",
            {"limit": 10, "updated_at__gte": "2100-01-01T00:00:00Z"},
        )
        assert future.status_code == 200, endpoint
        assert future.json()["count"] == 0, f"{endpoint}: expected no rows after 2100"

        window = authenticated_client.get(
            f"/api/{endpoint}/",
            {
                "limit": 10,
                "created_at__gte": "2000-01-01T00:00:00Z",
                "created_at__lt": "2100-01-01T00:00:00Z",
            },
        )
        assert window.status_code == 200, endpoint
        assert window.json()["count"] >= 1, f"{endpoint}: window filter dropped rows"

        invalid = authenticated_client.get(
            f"/api/{endpoint}/", {"updated_at__gte": "not-a-date"}
        )
        assert invalid.status_code == 400, f"{endpoint}: invalid date should 400"
