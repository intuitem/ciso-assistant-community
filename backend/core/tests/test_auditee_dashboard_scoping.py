"""The auditee dashboard must only list assignments the user can open.

The assessment page fetches the assignment through the scoped viewset
(`view_requirementassignment`), while the dashboard used to select assignments
by actor match alone: a user whose role grants audit access but not assignment
access would see a card whose "continue assessment" click 404s.
"""

from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from core.models import (
    Actor,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementAssignment,
    StoredLibrary,
)
from core.startup import startup
from iam.models import Folder, Role, RoleAssignment, User, UserGroup

FIXTURE = Path(__file__).parent / "fixtures" / "test-splash-assessable.yaml"


@pytest.fixture
def app_config():
    startup(sender=None, **{})


@pytest.fixture
def audit_with_assignment(app_config):
    stored, err = StoredLibrary.store_library_content(FIXTURE.read_bytes())
    assert err is None
    assert stored.load() is None
    framework = Framework.objects.get(
        urn="urn:intuitem:test:framework:splash-assessable"
    )
    domain = Folder.objects.create(
        name="DashboardScopingDomain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(domain)
    perimeter = Perimeter.objects.create(name="P1", folder=domain)
    ca = ComplianceAssessment.objects.create(
        name="Audit", framework=framework, perimeter=perimeter, folder=domain
    )
    ca.create_requirement_assessments()

    respondent = User.objects.create_user("respondent@dashboard-scoping-tests.com")
    actor, _ = Actor.objects.get_or_create(user=respondent)
    assignment = RequirementAssignment.objects.create(
        compliance_assessment=ca, folder=domain, status="in_progress"
    )
    assignment.actor.add(actor)
    assignment.requirement_assessments.set(
        RequirementAssessment.objects.filter(
            compliance_assessment=ca, requirement__assessable=True
        )
    )
    return domain, ca, respondent, assignment


@pytest.mark.django_db
def test_dashboard_hides_assignments_the_user_cannot_open(audit_with_assignment):
    domain, ca, respondent, assignment = audit_with_assignment

    # Custom role: audit access without assignment access.
    role = Role.objects.create(
        name="PartialRespondent", folder=Folder.get_root_folder()
    )
    role.permissions.set(
        Permission.objects.filter(
            codename__in=[
                "view_complianceassessment",
                "view_requirementassessment",
                "view_folder",
            ]
        )
    )
    ug = UserGroup.objects.create(name="PartialUG", folder=domain)
    ug.user_set.add(respondent)
    ra = RoleAssignment.objects.create(
        user_group=ug, role=role, folder=Folder.get_root_folder(), is_recursive=True
    )
    ra.perimeter_folders.add(domain)

    client = APIClient()
    client.force_authenticate(user=respondent)

    # The page the card links to is inaccessible...
    page = client.get(f"/api/requirement-assignments/{assignment.id}/")
    assert page.status_code == 404

    # ... so the dashboard must not advertise it.
    dash = client.get("/api/compliance-assessments/auditee-dashboard/")
    assert dash.status_code == 200
    assert dash.json() == []


@pytest.mark.django_db
def test_dashboard_lists_assignments_for_builtin_auditee(audit_with_assignment):
    domain, ca, respondent, assignment = audit_with_assignment

    auditee_group = UserGroup.objects.get(name="BI-UG-ADE", folder=domain)
    auditee_group.user_set.add(respondent)

    client = APIClient()
    client.force_authenticate(user=respondent)

    dash = client.get("/api/compliance-assessments/auditee-dashboard/")
    assert dash.status_code == 200
    cards = dash.json()
    assert len(cards) == 1
    assert cards[0]["assignment_id"] == str(assignment.id)

    # The card's target page loads.
    assert (
        client.get(f"/api/requirement-assignments/{assignment.id}/").status_code == 200
    )
    assert client.get(f"/api/compliance-assessments/{ca.id}/").status_code == 200
    assert (
        client.get(
            f"/api/requirement-assignments/{assignment.id}/requirements_list/"
        ).status_code
        == 200
    )
