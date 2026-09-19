"""Power BI connector contract tests.

The connector at automation/powerbi/connector/CisoAssistant.pq hard-codes
column names, JSON paths and types (v1 decision). This test loads the
shared contract (automation/powerbi/contract.json) and asserts that every
path the connector consumes is present in the live serializer output with
a compatible JSON type, so a serializer refactor cannot silently break
Power BI refreshes.
"""

import json
import math
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
        Campaign,
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
        RiskAcceptance,
        RiskAssessment,
        RiskMatrix,
        RiskScenario,
        SecurityException,
        TaskNode,
        TaskTemplate,
        Threat,
        Vulnerability,
    )
    from iam.models import Folder, User
    from tprm.models import Contract, Entity, EntityAssessment, Solution

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

    entity = Entity.objects.create(
        name="BI Entity",
        folder=domain,
        ref_id="ENT-1",
        mission="BI provider",
        reference_link="https://example.com/entity",
    )
    # Saving a User/Team/Entity creates its Actor (core.base_models), which is
    # what every owner/assignee M2M points at. A user-backed one is used here
    # because /api/actors/ only lists entity actors when the instance allows
    # assigning work to entities.
    approver = User.objects.create(email="bi-approver@tests.com")
    actor = approver.actor
    solution = Solution.objects.create(
        name="BI Solution",
        ref_id="SOL-1",
        provider_entity=entity,
        recipient_entity=entity,
        criticality=1,
    )
    contract = Contract.objects.create(
        name="BI Contract",
        ref_id="CTR-1",
        folder=domain,
        provider_entity=entity,
        beneficiary_entity=entity,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        annual_expense=1234.56,
        notice_period_entity=30,
        notice_period_provider=60,
    )
    entity_assessment = EntityAssessment.objects.create(
        name="BI Entity Assessment",
        folder=domain,
        entity=entity,
        perimeter=perimeter,
        compliance_assessment=compliance_assessment,
        criticality=2,
        version="1.0",
        eta=date.today(),
        due_date=date.today() + timedelta(days=30),
        expiry_date=date.today() + timedelta(days=365),
        observation="observation",
        reference_link="https://example.com/entity-assessment",
    )
    task_template = TaskTemplate.objects.create(
        name="BI Task Template",
        ref_id="TSK-1",
        folder=domain,
        task_date=date.today(),
        link="https://example.com/task",
    )
    # Occurrences are generated from the template; only fall back to an
    # explicit one if that ever stops happening.
    task_node = TaskNode.objects.filter(task_template=task_template).first()
    if task_node is None:
        task_node = TaskNode.objects.create(
            task_template=task_template,
            folder=domain,
            due_date=date.today(),
            scheduled_date=date.today(),
        )
    risk_acceptance = RiskAcceptance.objects.create(
        name="BI Risk Acceptance",
        folder=domain,
        approver=approver,
        expiry_date=date.today() + timedelta(days=180),
        justification="justification",
    )
    campaign = Campaign.objects.create(
        name="BI Campaign",
        folder=domain,
        start_date=date.today(),
        eta=date.today(),
        due_date=date.today() + timedelta(days=60),
    )

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
    applied_control.owner.add(actor)
    applied_control.assets.add(asset)
    finding.owner.add(actor)
    risk_scenario.owner.add(actor)
    asset.owner.add(actor)
    incident.owners.add(actor)
    contract.owner.add(actor)
    contract.solutions.add(solution)
    solution.assets.add(asset)
    entity_assessment.solutions.add(solution)
    # The occurrence reads assignees and controls off its template.
    task_template.assigned_to.add(actor)
    task_template.applied_controls.add(applied_control)
    risk_acceptance.risk_scenarios.add(risk_scenario)
    campaign.compliance_assessments.add(compliance_assessment)

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
        "task-nodes": task_node,
        "entity-assessments": entity_assessment,
        "contracts": contract,
        "risk-acceptances": risk_acceptance,
        "actors": actor,
        "entities": entity,
        "solutions": solution,
        "task-templates": task_template,
        "campaigns": campaign,
    }


# Base query params the connector sends for a table (CisoAssistant.pq,
# GetEntityTable's baseQuery), mirrored so the tests read the same rows.
ENDPOINT_QUERY = {"actors": {"include_third_parties": "true"}}


def _get_row(client, endpoint, obj_id):
    response = client.get(
        f"/api/{endpoint}/", {"limit": 1000, **ENDPOINT_QUERY.get(endpoint, {})}
    )
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
        # Every table the connector declares as foldable (foldDates = true in
        # CisoAssistant.pq): incremental refresh folds RangeStart/RangeEnd into
        # these params, and a filterset that silently drops `__lt` would widen
        # each partition to the whole table.
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
            "task-nodes",
            "entity-assessments",
            "contracts",
            "risk-acceptances",
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


#
# Pagination contract.
#
# The connector pages with limit/offset and derives its stride from the rows
# the server actually served, because `limit` is clamped to PAGINATE_MAX.
# These tests are a Python port of GetAllRows / GetTopRows
# (automation/powerbi/connector/CisoAssistant.pq) run against the live API,
# so the algorithm is exercised where CI can see it — M itself only runs on
# the Windows validation VM.
#

CONNECTOR_PAGE_SIZE = 5000  # `PageSize` in CisoAssistant.pq


def _connector_get_all_rows(client, endpoint, extra=None):
    query = dict(extra or {})
    first = client.get(
        f"/api/{endpoint}/", {**query, "limit": CONNECTOR_PAGE_SIZE, "offset": 0}
    )
    assert first.status_code == 200, f"{endpoint}: {first.status_code}"
    payload = first.json()
    rows = list(payload["results"])
    total = payload["count"]
    served = len(rows)
    page_count = 0 if served == 0 else math.ceil(total / served)
    for i in range(1, page_count):
        page = client.get(
            f"/api/{endpoint}/", {**query, "limit": served, "offset": i * served}
        )
        assert page.status_code == 200, f"{endpoint}: {page.status_code}"
        rows.extend(page.json()["results"])
    return total, rows


def _connector_get_top_rows(client, endpoint, count, extra=None):
    query = dict(extra or {})
    first_limit = min(CONNECTOR_PAGE_SIZE, count)
    first = client.get(
        f"/api/{endpoint}/", {**query, "limit": first_limit, "offset": 0}
    )
    assert first.status_code == 200, f"{endpoint}: {first.status_code}"
    payload = first.json()
    rows = list(payload["results"])
    served = len(rows)
    # A short page means either a clamped limit or the end of the table; only
    # `count` tells them apart, so the walk targets whichever is smaller.
    wanted = min(count, payload["count"])
    page_count = (
        0 if served == 0 or served >= wanted else math.ceil((wanted - served) / served)
    )
    for i in range(1, page_count + 1):
        page_limit = min(served, wanted - (i * served))
        page = client.get(
            f"/api/{endpoint}/",
            {**query, "limit": page_limit, "offset": i * served},
        )
        assert page.status_code == 200, f"{endpoint}: {page.status_code}"
        rows.extend(page.json()["results"])
    return rows[:count]


@pytest.fixture
def clamped_pagination(monkeypatch):
    """Serve tiny pages, the way an instance with a low PAGINATE_MAX does.

    `max_limit` is read off settings at class-definition time, so
    `override_settings` cannot move it.
    """
    from core.pagination import CustomLimitOffsetPagination

    monkeypatch.setattr(CustomLimitOffsetPagination, "max_limit", 2)
    return 2


@pytest.fixture
def many_applied_controls(bi_dataset):
    from core.models import AppliedControl

    folder = bi_dataset["applied-controls"].folder
    return [
        AppliedControl.objects.create(name=f"BI Paging Control {i}", folder=folder)
        for i in range(6)
    ]


@pytest.mark.django_db
def test_pagination_clamps_limit_but_keeps_true_count(
    authenticated_client, many_applied_controls, clamped_pagination
):
    """The premise the connector relies on: a clamped page still reports `count`."""
    response = authenticated_client.get(
        "/api/applied-controls/", {"limit": CONNECTOR_PAGE_SIZE, "offset": 0}
    )
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["results"]) == clamped_pagination
    assert payload["count"] > clamped_pagination
    assert payload["next"] is not None


@pytest.mark.django_db
def test_connector_paging_retrieves_every_row_when_clamped(
    authenticated_client, many_applied_controls, clamped_pagination
):
    total, rows = _connector_get_all_rows(authenticated_client, "applied-controls")

    assert total > clamped_pagination, "fixture must span more than one served page"
    assert len(rows) == total
    ids = [row["id"] for row in rows]
    assert len(set(ids)) == total, "offset paging returned duplicate rows"

    # Guard the specific defect fixed in connector 1.1.0: a stride taken from the
    # requested PageSize instead of the served length imports one page and stops.
    truncated = math.ceil(total / CONNECTOR_PAGE_SIZE) * clamped_pagination
    assert truncated < total, "fixture no longer reproduces the truncation"


@pytest.mark.django_db
def test_connector_paging_handles_empty_table(authenticated_client, clamped_pagination):
    total, rows = _connector_get_all_rows(
        authenticated_client,
        "applied-controls",
        extra={"updated_at__gte": "2100-01-01T00:00:00Z"},
    )

    assert total == 0
    assert rows == []


@pytest.mark.django_db
def test_connector_preview_paging_returns_requested_count(
    authenticated_client, many_applied_controls, clamped_pagination
):
    """OnTake previews carried the same defect as the full load."""
    total = authenticated_client.get("/api/applied-controls/", {"limit": 1}).json()[
        "count"
    ]
    wanted = total - 1
    assert wanted > clamped_pagination

    rows = _connector_get_top_rows(authenticated_client, "applied-controls", wanted)

    assert len(rows) == wanted
    assert len({row["id"] for row in rows}) == wanted


@pytest.mark.django_db
def test_powerbi_bridge_projection_is_accepted(authenticated_client, bi_dataset):
    """Bridges fetch `?fields=id,<m2m>`; an unknown name there is a 400.

    The connector falls back to the full row on error, so this failing means
    a silent loss of the optimisation rather than a broken refresh — but it
    is still drift, and the fallback should not become the normal path.
    """
    for bridge in CONTRACT["bridges"]:
        endpoint = bridge["endpoint"]
        list_field = bridge["list_field"]
        response = authenticated_client.get(
            f"/api/{endpoint}/", {"fields": f"id,{list_field}", "limit": 10}
        )
        assert response.status_code == 200, (
            f"{bridge['name']}: ?fields=id,{list_field} → {response.status_code}"
        )
        for row in response.json()["results"]:
            assert set(row) == {"id", list_field}, bridge["name"]


class _CountingClient:
    """Tallies the requests an algorithm issues, for cost assertions."""

    def __init__(self, client):
        self._client = client
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return self._client.get(*args, **kwargs)


@pytest.mark.django_db
def test_connector_preview_stops_at_the_end_of_a_short_table(
    authenticated_client, many_applied_controls, clamped_pagination
):
    """A preview may ask for far more rows than the table holds.

    The stride is the served page size, so without the envelope's `count` to
    bound it the walk keeps stepping toward the requested `count` long after
    the rows run out — one request per stride, all of them empty. The smaller
    the table, the more requests. Row counts stay correct throughout, which is
    why this is asserted on the number of calls.
    """
    total = authenticated_client.get("/api/applied-controls/", {"limit": 1}).json()[
        "count"
    ]
    client = _CountingClient(authenticated_client)

    rows = _connector_get_top_rows(client, "applied-controls", 1000)

    assert len(rows) == total
    assert client.calls == math.ceil(total / clamped_pagination)
