import pytest
from django.contrib.auth.models import Permission
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    Actor,
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Evidence,
    Finding,
    Framework,
    Incident,
    ReferenceControl,
    RequirementAssessment,
    RequirementAssignment,
    RequirementNode,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    TaskTemplate,
    Vulnerability,
)
from core.utils import RoleCodename
from crq.models import (
    QuantitativeRiskHypothesis,
    QuantitativeRiskScenario,
    QuantitativeRiskStudy,
)
from doc_management.models import DocumentContainer
from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import Folder, Role, RoleAssignment, User
from privacy.models import DataBreach
from sec_intel.models import TTPCatalog
from threat_modeling.models import ThreatModel, ThreatModelNode

URL = "/api/applied-controls/reliance/"


@pytest.fixture
def portfolio(db):
    root = Folder.get_root_folder()
    visible, hidden = (
        Folder.objects.create(
            name=name, parent_folder=root, content_type=Folder.ContentType.DOMAIN
        )
        for name in ("Operations", "Restricted")
    )
    user = User.objects.create_user("reliance@example.com")
    RoleAssignment.objects.create(
        user=user,
        role=Role.objects.get(name=RoleCodename.ANALYST.value),
        folder=root,
        is_recursive=True,
    ).perimeter_folders.add(visible)
    client = APIClient()
    client.force_authenticate(user)
    reference = ReferenceControl.objects.create(name="Access review", folder=visible)
    first = AppliedControl.objects.create(
        name="App access", folder=visible, reference_control=reference
    )
    second = AppliedControl.objects.create(
        name="Cloud access", folder=visible, reference_control=reference
    )
    supporting = AppliedControl.objects.create(
        name="Documentation only", folder=visible
    )
    concealed = AppliedControl.objects.create(
        name="Secret implementation", folder=hidden, reference_control=reference
    )
    framework = Framework.objects.create(name="Framework", folder=visible)
    requirement = RequirementNode.objects.create(
        framework=framework, folder=visible, assessable=True, ref_id="1"
    )
    requirement.reference_controls.add(reference)
    audit = ComplianceAssessment.objects.create(
        name="Audit", framework=framework, folder=visible
    )
    assessment = RequirementAssessment.objects.create(
        compliance_assessment=audit, requirement=requirement, folder=visible
    )
    assessment.applied_controls.add(first, second)
    matrix = RiskMatrix.objects.create(name="Matrix", folder=visible)
    risk = RiskAssessment.objects.create(
        name="Risk", folder=visible, risk_matrix=matrix
    )
    scenario = RiskScenario.objects.create(
        name="Unauthorized access", risk_assessment=risk
    )
    scenario.applied_controls.add(first)
    scenario.existing_applied_controls.add(first, second)
    private_risk = RiskAssessment.objects.create(
        name="Private risk", folder=hidden, risk_matrix=matrix
    )
    private_scenario = RiskScenario.objects.create(
        name="Private scenario", risk_assessment=private_risk
    )
    private_scenario.applied_controls.add(first, concealed)
    for i in range(4):
        supporting.evidences.add(
            Evidence.objects.create(name=f"Attachment {i}", folder=visible)
        )
    first.evidences.add(
        Evidence.objects.create(name="Secret attachment", folder=hidden)
    )
    doc = DocumentContainer.objects.create(name="Procedure", folder=visible)
    doc.applied_controls.add(first, second)
    Finding.objects.create(name="Access gap", folder=visible).applied_controls.add(
        first
    )
    return client, first, second, supporting, reference


def test_reliance_scores_only_visible_substantive_links(portfolio):
    client, first, second, supporting, _ = portfolio
    response = client.get(URL)
    assert response.status_code == 200, response.content
    rows = response.json()["applied_controls"]
    assert {row["id"] for row in rows} == {
        str(obj.id) for obj in (first, second, supporting)
    }
    rows = {row["id"]: row for row in rows}
    counts = rows[str(first.id)]["counts"]
    assert {key: count for key, count in counts.items() if count} == {
        "requirement_assessments": 1,
        "audits": 1,
        "risk_scenarios": 1,
        "risk_treatment": 1,
        "risk_existing": 1,
        "findings": 1,
        "documents": 1,
    }
    assert rows[str(first.id)]["score"] == 7
    assert rows[str(supporting.id)]["counts"]["evidences"] == 4
    assert rows[str(supporting.id)]["score"] == 0


def test_reference_rollup_deduplicates_and_keeps_catalog_mappings_separate(portfolio):
    client, _, _, _, reference = portfolio
    response = client.get(URL)
    assert response.status_code == 200, response.content
    (row,) = response.json()["reference_controls"]
    assert row["id"] == str(reference.id)
    assert row["implementations"] == 2
    assert row["counts"]["requirement_assessments"] == 1
    assert row["counts"]["risk_scenarios"] == 1
    assert row["counts"]["documents"] == 1
    assert row["catalog_requirements"] == 1
    assert row["score"] == 7


def test_catalog_only_reference_controls_are_visible_without_a_score(portfolio):
    client, first, _, _, _ = portfolio
    catalog_only = ReferenceControl.objects.create(
        name="Catalog only", folder=first.folder
    )
    hidden = ReferenceControl.objects.create(
        name="Hidden reference", folder=Folder.objects.get(name="Restricted")
    )
    RequirementNode.objects.get(ref_id="1", folder=first.folder).reference_controls.add(
        catalog_only, hidden
    )

    response = client.get(URL)
    assert response.status_code == 200, response.content
    rows = {row["id"]: row for row in response.json()["reference_controls"]}
    assert str(hidden.id) not in rows
    assert rows[str(catalog_only.id)]["catalog_requirements"] == 1
    assert rows[str(catalog_only.id)]["implementations"] == 0
    assert rows[str(catalog_only.id)]["score"] == 0


def test_reference_control_without_a_name_does_not_break_the_ranking(portfolio):
    client, _, _, _, reference = portfolio
    reference.name = None
    reference.ref_id = "AC-REF"
    reference.save(update_fields=["name", "ref_id"])

    response = client.get(URL)
    assert response.status_code == 200, response.content
    (row,) = response.json()["reference_controls"]
    assert row["id"] == str(reference.id)
    assert row["name"] == ""
    assert row["ref_id"] == "AC-REF"
    assert row["score"] > 0


def test_reliance_exposes_domain_and_updated_priority(portfolio):
    client, first, _, _, _ = portfolio
    detail = f"/api/applied-controls/{first.id}/"
    for priority in (1, None):
        response = client.patch(detail, {"priority": priority}, format="json")
        assert response.status_code == 200, response.content
        assert response.json()["priority"] == priority
        response = client.get(URL)
        assert response.status_code == 200, response.content
        row = next(
            r for r in response.json()["applied_controls"] if r["id"] == str(first.id)
        )
        assert row["domain"] == first.folder.name
        assert row["priority"] == priority
        assert row["can_edit_priority"] is True


def test_reliance_disables_priority_editing_for_readers(portfolio):
    _, first, _, _, _ = portfolio
    user = User.objects.create_user("reliance-reader@example.com")
    RoleAssignment.objects.create(
        user=user,
        role=Role.objects.get(name=RoleCodename.READER.value),
        folder=Folder.get_root_folder(),
        is_recursive=True,
    ).perimeter_folders.add(first.folder)
    client = APIClient()
    client.force_authenticate(user)
    response = client.get(URL)
    assert response.status_code == 200, response.content
    row = next(
        r for r in response.json()["applied_controls"] if r["id"] == str(first.id)
    )
    assert row["can_edit_priority"] is False
    response = client.patch(
        f"/api/applied-controls/{first.id}/", {"priority": 1}, format="json"
    )
    assert response.status_code == 403


def test_remediation_counts_open_vulnerabilities_and_breaches_but_not_incidents(
    portfolio,
):
    client, first, second, supporting, _ = portfolio
    folder = first.folder
    for name, status in (
        ("Open", Vulnerability.Status.EXPLOITABLE),
        ("Fixed", Vulnerability.Status.FIXED),
    ):
        Vulnerability.objects.create(
            name=name, folder=folder, status=status
        ).applied_controls.add(first, second)
    Vulnerability.objects.create(
        name="Hidden", folder=Folder.objects.get(name="Restricted")
    ).applied_controls.add(first)
    incident = Incident.objects.create(name="Incident", folder=folder)
    incident.applied_controls.add(first, supporting)
    DataBreach.objects.create(
        name="Breach", folder=folder, incident=incident, discovered_on=timezone.now()
    ).remediation_measures.add(first, second)

    response = client.get(URL)
    assert response.status_code == 200, response.content
    rows = {r["id"]: r for r in response.json()["applied_controls"]}
    (reference,) = response.json()["reference_controls"]
    for row in (rows[str(first.id)], reference):
        assert row["counts"]["open_vulnerabilities"] == 1
        assert row["counts"]["resolved_vulnerabilities"] == 1
        assert row["counts"]["data_breaches"] == 1
        assert row["counts"]["incidents"] == 1
        assert row["score"] == 11
    assert rows[str(supporting.id)]["counts"]["incidents"] == 1
    assert rows[str(supporting.id)]["score"] == 0


def test_quantitative_risk_scores_distinct_existing_scenarios_only(portfolio):
    client, first, second, supporting, _ = portfolio
    folder = first.folder
    study = QuantitativeRiskStudy.objects.create(name="Study", folder=folder)
    scenario = QuantitativeRiskScenario.objects.create(
        name="Scenario", quantitative_risk_study=study, folder=folder
    )
    for name in ("Baseline", "Alternative"):
        hypothesis = QuantitativeRiskHypothesis.objects.create(
            name=name, quantitative_risk_scenario=scenario, folder=folder
        )
        hypothesis.existing_applied_controls.add(first, second)
        hypothesis.added_applied_controls.add(supporting)
        hypothesis.removed_applied_controls.add(supporting)

    hidden_folder = Folder.objects.get(name="Restricted")
    QuantitativeRiskHypothesis.objects.create(
        name="Hidden hypothesis",
        quantitative_risk_scenario=scenario,
        folder=hidden_folder,
    ).existing_applied_controls.add(supporting)
    hidden_scenario = QuantitativeRiskScenario.objects.create(
        name="Hidden scenario", quantitative_risk_study=study, folder=hidden_folder
    )
    QuantitativeRiskHypothesis.objects.create(
        name="Visible hypothesis",
        quantitative_risk_scenario=hidden_scenario,
        folder=folder,
    ).existing_applied_controls.add(first)

    response = client.get(URL)
    assert response.status_code == 200, response.content
    rows = {r["id"]: r for r in response.json()["applied_controls"]}
    (reference,) = response.json()["reference_controls"]
    for row in (rows[str(first.id)], reference):
        assert row["counts"]["quantitative_risk_existing"] == 1
        assert row["score"] == 10
    context = rows[str(supporting.id)]
    assert context["counts"]["quantitative_risk_added"] == 1
    assert context["counts"]["quantitative_risk_removed"] == 1
    assert context["score"] == 0


@pytest.mark.parametrize("threat_modeling", [False, True])
def test_alternate_audit_count_and_operational_context_are_deduplicated(
    portfolio, threat_modeling
):
    client, first, second, _, _ = portfolio
    flags = GlobalSettings.objects.get(name=GlobalSettings.Names.FEATURE_FLAGS)
    flags.value = {**flags.value, "threat_modeling": threat_modeling}
    flags.save()
    clear_feature_flags_cache()
    folder = first.folder
    audit = ComplianceAssessment.objects.get(name="Audit")
    requirement = RequirementNode.objects.create(
        framework=audit.framework, folder=folder, assessable=True, ref_id="2"
    )
    RequirementAssessment.objects.create(
        compliance_assessment=audit, requirement=requirement, folder=folder
    ).applied_controls.add(first, second)
    first.assets.add(Asset.objects.create(name="Application", folder=folder))
    for name, enabled in (("Enabled", True), ("Disabled", False)):
        TaskTemplate.objects.create(
            name=name, folder=folder, enabled=enabled, is_recurrent=True
        ).applied_controls.add(first, second)
    catalog = TTPCatalog.objects.create(name="Catalog", folder=folder)
    model = ThreatModel.objects.create(
        name="Threat model", folder=folder, catalog=catalog
    )
    for label in ("Node one", "Node two"):
        ThreatModelNode.objects.create(
            threat_model=model, kind="custom", label=label
        ).applied_controls.add(first, second)

    response = client.get(URL)
    assert response.status_code == 200, response.content
    (row,) = response.json()["reference_controls"]
    assert row["counts"]["requirement_assessments"] == 2
    assert row["counts"]["audits"] == 1
    assert row["counts"]["assets"] == 1
    assert row["counts"]["recurring_tasks"] == 1
    assert row["counts"]["threat_models"] == int(threat_modeling)
    assert row["score"] == 9


@pytest.mark.parametrize("field_access, expected", [("read", 1), ("hidden", 0)])
def test_reliance_respects_auditee_assignments_and_field_visibility(
    portfolio, field_access, expected
):
    _, first, _, _, _ = portfolio
    folder = first.folder
    user = User.objects.create_user("reliance-auditee@example.com")
    RoleAssignment.objects.create(
        user=user,
        role=Role.objects.get(name=RoleCodename.AUDITEE.value),
        folder=Folder.get_root_folder(),
        is_recursive=True,
    ).perimeter_folders.add(folder)
    audit = ComplianceAssessment.objects.get(name="Audit")
    audit.field_visibility = {"applied_controls": {"respondent": field_access}}
    audit.save(update_fields=["field_visibility"])
    assigned = RequirementAssessment.objects.get(compliance_assessment=audit)
    assignment = RequirementAssignment.objects.create(
        compliance_assessment=audit, folder=folder
    )
    assignment.actor.set(Actor.get_all_for_user(user))
    assignment.requirement_assessments.add(assigned)
    other_node = RequirementNode.objects.create(
        framework=audit.framework, folder=folder, ref_id="2", assessable=True
    )
    RequirementAssessment.objects.create(
        compliance_assessment=audit, requirement=other_node, folder=folder
    ).applied_controls.add(first)

    client = APIClient()
    client.force_authenticate(user)
    response = client.get(URL)
    assert response.status_code == 200, response.content
    row = next(
        r for r in response.json()["applied_controls"] if r["id"] == str(first.id)
    )
    assert row["counts"]["requirement_assessments"] == expected
    assert row["counts"]["audits"] == expected
    assert row["score"] == 2 * expected


def test_reliance_only_displays_domain_names_the_caller_can_view(portfolio):
    _, first, _, _, _ = portfolio
    user = User.objects.create_user("reliance-control-only@example.com")
    role = Role.objects.create(name="Controls only")
    role.permissions.add(Permission.objects.get(codename="view_appliedcontrol"))
    RoleAssignment.objects.create(
        user=user, role=role, folder=Folder.get_root_folder(), is_recursive=True
    ).perimeter_folders.add(first.folder)
    client = APIClient()
    client.force_authenticate(user)
    response = client.get(URL)
    assert response.status_code == 200, response.content
    row = next(
        r for r in response.json()["applied_controls"] if r["id"] == str(first.id)
    )
    assert row["domain"] == ""
