import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import (
    AppliedControl,
    Evidence,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
)
from core.views import ComplianceAssessmentViewSet, FolderViewSet
from test_fixtures import RISK_MATRIX_JSON_DEFINITION
from iam.models import Folder, User


@pytest.fixture
def audit_with_shared_control():
    """Audit whose requirements all point at the same applied control."""
    root_folder = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root_folder, name="quality check")
    perimeter = Perimeter.objects.create(name="quality check", folder=folder)
    framework = Framework.objects.create(
        name="Quality Check Framework",
        urn="urn:test:quality-check-framework",
        folder=root_folder,
    )
    for index in range(3):
        RequirementNode.objects.create(
            framework=framework,
            urn=f"urn:test:quality-check-framework:req{index}",
            ref_id=f"REQ-{index}",
            name=f"Requirement {index}",
            assessable=True,
            folder=root_folder,
        )
    compliance_assessment = ComplianceAssessment.objects.create(
        name="Quality check audit",
        framework=framework,
        perimeter=perimeter,
        folder=folder,
    )
    compliance_assessment.create_requirement_assessments()
    control = AppliedControl.objects.create(name="Shared control", folder=folder)
    for ra in compliance_assessment.requirement_assessments.all():
        ra.applied_controls.add(control)
    return compliance_assessment, control


@pytest.mark.django_db
def test_shared_control_is_reported_once(audit_with_shared_control):
    compliance_assessment, control = audit_with_shared_control

    findings = compliance_assessment.quality_check()

    reported = [
        f for f in findings["info"] if f["msgid"] == "appliedControlNoReferenceControl"
    ]
    assert len(reported) == 1
    assert reported[0]["link"] == f"applied-controls/{control.id}"


@pytest.mark.django_db
def test_query_count_does_not_grow_with_requirements(audit_with_shared_control):
    compliance_assessment, _ = audit_with_shared_control

    with CaptureQueriesContext(connection) as baseline:
        compliance_assessment.quality_check()

    framework = compliance_assessment.framework
    # Assessments are created here rather than through
    # create_requirement_assessments(), which would add a second assessment for
    # the three requirements the audit already covers.
    for index in range(3, 20):
        requirement = RequirementNode.objects.create(
            framework=framework,
            urn=f"urn:test:quality-check-framework:req{index}",
            ref_id=f"REQ-{index}",
            name=f"Requirement {index}",
            assessable=True,
            folder=Folder.get_root_folder(),
        )
        RequirementAssessment.objects.create(
            compliance_assessment=compliance_assessment,
            requirement=requirement,
            folder=compliance_assessment.folder,
        )
    assert (
        RequirementAssessment.objects.filter(
            compliance_assessment=compliance_assessment
        ).count()
        == RequirementNode.objects.filter(framework=framework).count()
        == 20
    )

    with CaptureQueriesContext(connection) as grown:
        compliance_assessment.quality_check()

    assert len(grown) == len(baseline)


@pytest.mark.django_db
def test_folders_without_findings_are_left_out(audit_with_shared_control):
    compliance_assessment, _ = audit_with_shared_control
    quiet_folder = Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="quiet domain",
        content_type=Folder.ContentType.DOMAIN,
    )
    user = User.objects.create_superuser("quality-check@tests.com")

    request = APIRequestFactory().get("/api/folders/quality_check/")
    force_authenticate(request, user=user)
    response = FolderViewSet.as_view({"get": "quality_check"})(request)

    assert response.status_code == 200
    results = response.data["results"]
    assert str(compliance_assessment.folder_id) in results
    assert str(quiet_folder.id) not in results
    assert all(FolderViewSet._has_findings(entry) for entry in results.values())


@pytest.mark.django_db
def test_evidence_attached_directly_to_a_requirement_is_checked(
    audit_with_shared_control,
):
    """Evidence reaches an audit through a requirement assessment as well as
    through an applied control; the file check has to follow both paths."""
    compliance_assessment, _ = audit_with_shared_control
    evidence = Evidence.objects.create(
        name="Direct evidence", folder=compliance_assessment.folder
    )
    requirement_assessment = compliance_assessment.requirement_assessments.first()
    requirement_assessment.evidences.add(evidence)

    findings = compliance_assessment.quality_check()

    reported = [f for f in findings["warnings"] if f["msgid"] == "evidenceNoFile"]
    assert [f["link"] for f in reported] == [f"evidences/{evidence.id}"]


@pytest.mark.django_db
def test_active_control_without_evidence_is_reported(audit_with_shared_control):
    compliance_assessment, control = audit_with_shared_control
    control.status = AppliedControl.Status.ACTIVE
    control.save()

    reported = [
        f
        for f in compliance_assessment.quality_check()["warnings"]
        if f["msgid"] == "appliedControlActiveNoEvidence"
    ]
    assert [f["link"] for f in reported] == [f"applied-controls/{control.id}"]

    control.evidences.add(
        Evidence.objects.create(name="Proof", folder=compliance_assessment.folder)
    )

    assert not [
        f
        for f in compliance_assessment.quality_check()["warnings"]
        if f["msgid"] == "appliedControlActiveNoEvidence"
    ]


@pytest.mark.django_db
def test_existing_control_without_evidence_is_reported():
    """Existing controls reach the assessment through `risk_scenarios_e`."""
    root_folder = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root_folder, name="existing control")
    perimeter = Perimeter.objects.create(name="existing control", folder=folder)
    matrix = RiskMatrix.objects.create(
        name="quality check matrix",
        json_definition=RISK_MATRIX_JSON_DEFINITION,
        folder=root_folder,
    )
    risk_assessment = RiskAssessment.objects.create(
        name="existing control",
        perimeter=perimeter,
        risk_matrix=matrix,
        folder=folder,
    )
    scenario = RiskScenario.objects.create(
        name="scenario", risk_assessment=risk_assessment, folder=folder
    )
    control = AppliedControl.objects.create(
        name="Existing control", folder=folder, status=AppliedControl.Status.ACTIVE
    )
    scenario.existing_applied_controls.add(control)

    reported = [
        f
        for f in risk_assessment.quality_check()["warnings"]
        if f["msgid"] == "appliedControlActiveNoEvidence"
    ]
    assert [f["link"] for f in reported] == [f"applied-controls/{control.id}"]


@pytest.mark.django_db
def test_control_that_is_not_active_needs_no_evidence(audit_with_shared_control):
    compliance_assessment, control = audit_with_shared_control
    control.status = AppliedControl.Status.TO_DO
    control.save()

    assert not [
        f
        for f in compliance_assessment.quality_check()["warnings"]
        if f["msgid"] == "appliedControlActiveNoEvidence"
    ]


@pytest.mark.django_db
def test_ordering_by_authors_works_outside_the_list_action(audit_with_shared_control):
    """`ordering_remap` rewrites `authors` on every action, not just `list`, so
    the annotation it points at has to be there too. Any action handed the list
    query string -- the autocomplete endpoint here, the CSV export once it is
    wired -- used to raise FieldError on the rewritten column."""
    user = User.objects.create_superuser("ordering@tests.com")

    request = APIRequestFactory().get(
        "/api/compliance-assessments/autocomplete/", {"ordering": "authors"}
    )
    force_authenticate(request, user=user)
    response = ComplianceAssessmentViewSet.as_view({"get": "autocomplete"})(request)

    assert response.status_code == 200
