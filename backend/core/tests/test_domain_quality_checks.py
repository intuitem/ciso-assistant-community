from datetime import date, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from core.domain_quality_checks import domain_quality_checks, object_quality_checks
from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    Finding,
    FindingsAssessment,
    Framework,
    OrganisationIssue,
    OrganisationObjective,
    RequirementAssignment,
    RequirementNode,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    Severity,
    TaskNode,
    TaskTemplate,
)
from core.views import ComplianceAssessmentViewSet, FolderViewSet
from test_fixtures import RISK_MATRIX_JSON_DEFINITION
from core.startup import startup
from iam.models import Folder, Role, RoleAssignment, RoleCodename, User, UserGroup

TODAY = date(2026, 9, 26)
PAST = TODAY - timedelta(days=1)
FUTURE = TODAY + timedelta(days=1)


@pytest.fixture
def domain():
    return Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="x-rays domain",
        content_type=Folder.ContentType.DOMAIN,
    )


@pytest.fixture
def admin():
    return User.objects.create_superuser("xrays-domain@tests.com")


def _flagged(domain, admin, block, severity, msgid):
    res = domain_quality_checks(Folder.objects.filter(pk=domain.pk), admin, TODAY)
    return {
        issue["object"]["id"]
        for issue in res[str(domain.id)][block][severity]
        if issue["msgid"] == msgid
    }


@pytest.mark.django_db
def test_objective_without_control_nor_task(domain, admin):
    bare = OrganisationObjective.objects.create(name="bare", folder=domain)
    with_control = OrganisationObjective.objects.create(name="ctrl", folder=domain)
    AppliedControl.objects.create(name="c", folder=domain).objectives.add(with_control)
    with_task = OrganisationObjective.objects.create(name="task", folder=domain)
    with_task.tasks.add(TaskTemplate.objects.create(name="t", folder=domain))
    OrganisationObjective.objects.create(
        name="achieved", folder=domain, status=OrganisationObjective.Status.ACHIEVED
    )
    OrganisationObjective.objects.create(
        name="inactive", folder=domain, is_active=False
    )

    assert _flagged(
        domain, admin, "governance", "warnings", "objectiveNoAppliedControlOrTask"
    ) == {bare.id}


@pytest.mark.django_db
def test_objective_overdue_and_contradictory_health(domain, admin):
    overdue = OrganisationObjective.objects.create(
        name="overdue", folder=domain, due_date=PAST
    )
    OrganisationObjective.objects.create(name="future", folder=domain, due_date=FUTURE)
    OrganisationObjective.objects.create(
        name="done",
        folder=domain,
        due_date=PAST,
        status=OrganisationObjective.Status.ACHIEVED,
    )
    contradictory = OrganisationObjective.objects.create(
        name="contradictory",
        folder=domain,
        status=OrganisationObjective.Status.ACHIEVED,
        health=OrganisationObjective.Health.OFF_TRACK,
    )

    assert _flagged(domain, admin, "governance", "warnings", "objectiveOverdue") == {
        overdue.id
    }
    assert _flagged(
        domain, admin, "governance", "warnings", "objectiveAchievedNotOnTrack"
    ) == {contradictory.id}
    assert contradictory.id not in _flagged(
        domain, admin, "governance", "info", "objectiveNoMetric"
    )
    assert overdue.id in _flagged(
        domain, admin, "governance", "info", "objectiveNoMetric"
    )


@pytest.mark.django_db
def test_active_issue_without_objective(domain, admin):
    orphan = OrganisationIssue.objects.create(
        name="orphan", folder=domain, status=OrganisationIssue.Status.ACTIVE
    )
    covered = OrganisationIssue.objects.create(
        name="covered", folder=domain, status=OrganisationIssue.Status.ACTIVE
    )
    OrganisationObjective.objects.create(name="o", folder=domain).issues.add(covered)
    OrganisationIssue.objects.create(name="draft", folder=domain)

    assert _flagged(
        domain, admin, "governance", "info", "organisationIssueNoObjective"
    ) == {orphan.id}


@pytest.mark.django_db
def test_evidence_rules(domain, admin):
    missing = Evidence.objects.create(
        name="missing", folder=domain, status=Evidence.Status.MISSING
    )
    expired = Evidence.objects.create(
        name="expired",
        folder=domain,
        status=Evidence.Status.EXPIRED,
        expiry_date=PAST,
    )
    stale = Evidence.objects.create(
        name="stale",
        folder=domain,
        status=Evidence.Status.APPROVED,
        expiry_date=PAST,
    )
    Evidence.objects.create(
        name="fine",
        folder=domain,
        status=Evidence.Status.APPROVED,
        expiry_date=FUTURE,
    )

    assert _flagged(domain, admin, "governance", "warnings", "evidenceMissing") == {
        missing.id
    }
    assert _flagged(domain, admin, "governance", "warnings", "evidenceExpired") == {
        expired.id
    }
    assert _flagged(
        domain, admin, "governance", "warnings", "evidenceExpiryDatePassed"
    ) == {stale.id}


@pytest.mark.django_db
def test_finding_rules(domain, admin):
    blank = Finding.objects.create(name="blank", folder=domain)
    open_bare = Finding.objects.create(
        name="open",
        folder=domain,
        status=Finding.Status.CONFIRMED,
        severity=Severity.HIGH,
    )
    open_covered = Finding.objects.create(
        name="covered",
        folder=domain,
        status=Finding.Status.CONFIRMED,
        severity=Severity.HIGH,
    )
    open_covered.applied_controls.add(
        AppliedControl.objects.create(name="c", folder=domain)
    )
    Finding.objects.create(
        name="closed",
        folder=domain,
        status=Finding.Status.CLOSED,
        severity=Severity.LOW,
    )

    assert _flagged(domain, admin, "governance", "warnings", "findingNoStatus") == {
        blank.id
    }
    assert _flagged(domain, admin, "governance", "warnings", "findingNoSeverity") == {
        blank.id
    }
    assert _flagged(
        domain, admin, "governance", "warnings", "findingNoAppliedControl"
    ) == {open_bare.id}


@pytest.mark.django_db
def test_applied_control_rules(domain, admin):
    blank = AppliedControl.objects.create(name="blank", folder=domain)
    planned = AppliedControl.objects.create(
        name="planned", folder=domain, status=AppliedControl.Status.TO_DO
    )
    active = AppliedControl.objects.create(
        name="active", folder=domain, status=AppliedControl.Status.ACTIVE
    )
    owned = AppliedControl.objects.create(
        name="owned",
        folder=domain,
        status=AppliedControl.Status.IN_PROGRESS,
        eta=FUTURE,
    )
    owned.owner.add(admin.actor)
    deprecated = AppliedControl.objects.create(
        name="deprecated", folder=domain, status=AppliedControl.Status.DEPRECATED
    )

    no_owner = _flagged(
        domain, admin, "operations", "warnings", "appliedControlNoOwner"
    )
    assert no_owner == {blank.id, planned.id, active.id}
    assert deprecated.id not in no_owner
    assert _flagged(domain, admin, "operations", "warnings", "appliedControlNoEta") == {
        planned.id
    }
    assert _flagged(
        domain, admin, "operations", "warnings", "appliedControlNoStatus"
    ) == {blank.id}


@pytest.mark.django_db
def test_task_rules(domain, admin):
    unassigned = TaskTemplate.objects.create(name="unassigned", folder=domain)
    assigned = TaskTemplate.objects.create(name="assigned", folder=domain)
    assigned.assigned_to.add(admin.actor)
    TaskTemplate.objects.create(name="disabled", folder=domain, enabled=False)
    TaskNode.objects.filter(task_template__folder=domain).delete()
    overdue = TaskNode.objects.create(
        task_template=assigned, folder=domain, due_date=PAST
    )
    TaskNode.objects.create(
        task_template=assigned,
        folder=domain,
        due_date=PAST - timedelta(days=1),
        status="completed",
    )
    TaskNode.objects.create(task_template=assigned, folder=domain, due_date=FUTURE)

    assert _flagged(
        domain, admin, "operations", "warnings", "taskTemplateNoAssignee"
    ) == {unassigned.id}
    assert _flagged(domain, admin, "operations", "warnings", "taskNodeOverdue") == {
        overdue.id
    }
    res = domain_quality_checks(Folder.objects.filter(pk=domain.pk), admin, TODAY)
    issue = next(
        i
        for i in res[str(domain.id)]["operations"]["warnings"]
        if i["msgid"] == "taskNodeOverdue"
    )
    assert issue["object"]["name"] == "assigned"
    assert issue["link"] == f"task-nodes/{overdue.id}"


@pytest.mark.django_db
def test_query_count_does_not_grow_with_objects(domain, admin):
    folders = Folder.objects.filter(pk=domain.pk)
    AppliedControl.objects.create(name="c0", folder=domain)
    domain_quality_checks(folders, admin, TODAY)
    with CaptureQueriesContext(connection) as baseline:
        domain_quality_checks(folders, admin, TODAY)
    for index in range(1, 20):
        AppliedControl.objects.create(name=f"c{index}", folder=domain)
        Finding.objects.create(name=f"f{index}", folder=domain)
    with CaptureQueriesContext(connection) as grown:
        domain_quality_checks(folders, admin, TODAY)
    assert len(grown) == len(baseline)


@pytest.mark.django_db
def test_invisible_objects_are_not_reported(domain):
    AppliedControl.objects.create(name="hidden", folder=domain)
    outsider = User.objects.create_user("xrays-outsider@tests.com")
    res = domain_quality_checks(Folder.objects.filter(pk=domain.pk), outsider, TODAY)
    assert res[str(domain.id)]["operations"]["count"] == 0


@pytest.mark.django_db
def test_domain_with_only_governance_findings_is_listed(domain, admin):
    OrganisationObjective.objects.create(name="bare", folder=domain)
    request = APIRequestFactory().get("/api/folders/quality_check/")
    force_authenticate(request, user=admin)
    response = FolderViewSet.as_view({"get": "quality_check"})(request)

    assert response.status_code == 200
    entry = response.data["results"][str(domain.id)]
    assert entry["governance"]["count"] > 0
    assert entry["operations"]["count"] == 0


@pytest.fixture
def audit(domain):
    framework = Framework.objects.create(
        name="X-rays framework",
        urn="urn:test:xrays-framework",
        folder=Folder.get_root_folder(),
    )
    RequirementNode.objects.create(
        framework=framework,
        urn="urn:test:xrays-framework:req",
        ref_id="REQ",
        name="Requirement",
        assessable=True,
        folder=Folder.get_root_folder(),
    )
    audit = ComplianceAssessment.objects.create(
        name="X-rays audit", framework=framework, folder=domain
    )
    audit.create_requirement_assessments()
    return audit


@pytest.mark.django_db
def test_audit_scope_only_reports_its_own_objects(domain, admin, audit):
    requirement_assessment = audit.requirement_assessments.first()
    linked = AppliedControl.objects.create(name="linked", folder=domain)
    requirement_assessment.applied_controls.add(linked)
    AppliedControl.objects.create(name="unrelated", folder=domain)
    stale = Evidence.objects.create(
        name="stale", folder=domain, status=Evidence.Status.MISSING
    )
    linked.evidences.add(stale)
    Evidence.objects.create(name="other", folder=domain, status=Evidence.Status.MISSING)
    binder = FindingsAssessment.objects.create(
        name="binder", folder=domain, compliance_assessment=audit
    )
    raised = Finding.objects.create(
        name="raised", folder=domain, findings_assessment=binder
    )
    Finding.objects.create(name="loose", folder=domain)
    task = TaskTemplate.objects.create(name="task", folder=domain)
    task.compliance_assessments.add(audit)

    res = object_quality_checks(audit, admin, TODAY)

    def ids(block, msgid):
        return {
            i["object"]["id"]
            for i in res[block]["warnings"] + res[block]["info"]
            if i["msgid"] == msgid
        }

    assert ids("operations", "appliedControlNoOwner") == {linked.id}
    assert ids("governance", "evidenceMissing") == {stale.id}
    assert ids("governance", "findingNoStatus") == {raised.id}
    assert ids("operations", "taskTemplateNoAssignee") == {task.id}
    assert res["governance"]["count"] == len(res["governance"]["warnings"]) + len(
        res["governance"]["info"]
    )


@pytest.mark.django_db
def test_risk_assessment_scope_covers_both_control_links(domain, admin):
    risk_matrix = RiskMatrix.objects.create(
        name="m",
        folder=Folder.get_root_folder(),
        json_definition=RISK_MATRIX_JSON_DEFINITION,
    )
    risk_assessment = RiskAssessment.objects.create(
        name="ra", folder=domain, risk_matrix=risk_matrix
    )
    scenario = RiskScenario.objects.create(name="s", risk_assessment=risk_assessment)
    planned = AppliedControl.objects.create(name="planned", folder=domain)
    existing = AppliedControl.objects.create(name="existing", folder=domain)
    scenario.applied_controls.add(planned)
    scenario.existing_applied_controls.add(existing)
    AppliedControl.objects.create(name="unrelated", folder=domain)

    res = object_quality_checks(risk_assessment, admin, TODAY)

    assert {
        i["object"]["id"]
        for i in res["operations"]["warnings"]
        if i["msgid"] == "appliedControlNoOwner"
    } == {planned.id, existing.id}


@pytest.mark.django_db
def test_x_rays_endpoint_returns_the_full_envelope(domain, admin, audit):
    AppliedControl.objects.create(
        name="linked", folder=domain
    ).requirement_assessments.add(audit.requirement_assessments.first())
    request = APIRequestFactory().get(f"/api/compliance-assessments/{audit.id}/x-rays/")
    force_authenticate(request, user=admin)
    response = ComplianceAssessmentViewSet.as_view({"get": "x_rays"})(
        request, pk=str(audit.id)
    )

    assert response.status_code == 200
    assert response.data["object"] == {
        "id": audit.id,
        "name": audit.name,
        "type": "complianceassessment",
    }
    assert set(response.data) == {"object", "assessment", "governance", "operations"}
    assert response.data["operations"]["count"] > 0


@pytest.mark.django_db
def test_x_rays_endpoint_hides_audits_the_user_cannot_see(audit):
    outsider = User.objects.create_user("xrays-outsider-audit@tests.com")
    request = APIRequestFactory().get(f"/api/compliance-assessments/{audit.id}/x-rays/")
    force_authenticate(request, user=outsider)
    response = ComplianceAssessmentViewSet.as_view({"get": "x_rays"})(
        request, pk=str(audit.id)
    )

    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role_name, expected",
    [(RoleCodename.AUDITEE.value, 403), (RoleCodename.READER.value, 200)],
)
def test_x_rays_endpoint_is_closed_to_respondents(domain, audit, role_name, expected):
    startup(sender=None, **{})
    user = User.objects.create_user(f"xrays-{role_name}@tests.com")
    group = UserGroup.objects.create(name=f"xrays-{role_name}", folder=domain)
    group.user_set.add(user)
    RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=role_name),
        folder=domain,
        is_recursive=True,
    ).perimeter_folders.add(domain)
    assignment = RequirementAssignment.objects.create(
        compliance_assessment=audit, folder=domain
    )
    assignment.actor.add(user.actor)
    assignment.requirement_assessments.set(audit.requirement_assessments.all())

    client = APIClient()
    client.force_authenticate(user)
    response = client.get(f"/api/compliance-assessments/{audit.id}/x-rays/")

    assert response.status_code == expected
