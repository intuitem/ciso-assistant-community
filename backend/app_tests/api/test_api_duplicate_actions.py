"""Folder scoping of the duplicate actions: the target folder must be one the
requesting user can create objects in, exactly as on a regular create."""

import pytest
from rest_framework.test import APIClient
from knox.models import AuthToken

from core.models import (
    AppliedControl,
    OrganisationObjective,
    Perimeter,
    RiskAssessment,
    RiskMatrix,
)
from iam.models import Folder, User, UserGroup

MATRIX_DEFINITION = {
    "type": "risk_matrix",
    "name": "3x3",
    "description": "",
    "probability": [
        {"abbreviation": "L", "name": "Low", "description": ""},
        {"abbreviation": "M", "name": "Medium", "description": ""},
        {"abbreviation": "H", "name": "High", "description": ""},
    ],
    "impact": [
        {"abbreviation": "L", "name": "Low", "description": ""},
        {"abbreviation": "M", "name": "Medium", "description": ""},
        {"abbreviation": "H", "name": "High", "description": ""},
    ],
    "risk": [
        {"abbreviation": "L", "name": "Low", "description": "", "hexcolor": "#fff"},
        {"abbreviation": "M", "name": "Medium", "description": "", "hexcolor": "#fff"},
        {"abbreviation": "H", "name": "High", "description": "", "hexcolor": "#fff"},
    ],
    "grid": [[0, 1, 2], [0, 1, 2], [0, 1, 2]],
}


def _make_domain(name):
    folder = Folder.objects.create(
        name=name,
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(folder)
    return folder


def _client_for(email, memberships):
    """Authenticated client for a fresh user added to ``(group_name, folder)`` pairs."""
    user = User.objects.create_user(email, is_published=True)
    for group_name, folder in memberships:
        group = UserGroup.objects.get(name=group_name, folder=folder)
        group.user_set.add(user)
    user.folder = memberships[0][1]
    user.save()
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def domains(app_config, db):
    return _make_domain("dup-domain-a"), _make_domain("dup-domain-b")


# --- applied controls ---------------------------------------------------------


@pytest.mark.django_db
def test_applied_control_duplicate_same_domain(domains):
    domain_a, _ = domains
    client = _client_for("dup-ana-a@tests.com", [("BI-UG-ANA", domain_a)])
    control = AppliedControl.objects.create(name="ctl", folder=domain_a)

    response = client.post(
        f"/api/applied-controls/{control.id}/duplicate/",
        {
            "name": "ctl copy",
            "description": "",
            "folder": str(domain_a.id),
            "duplicate_evidences": False,
        },
        format="json",
    )

    assert response.status_code == 200, response.content
    assert AppliedControl.objects.filter(name="ctl copy", folder=domain_a).exists()


@pytest.mark.django_db
def test_applied_control_duplicate_requires_rights_on_target_domain(domains):
    domain_a, domain_b = domains
    client = _client_for("dup-ana-a@tests.com", [("BI-UG-ANA", domain_a)])
    control = AppliedControl.objects.create(name="ctl", folder=domain_a)

    response = client.post(
        f"/api/applied-controls/{control.id}/duplicate/",
        {
            "name": "ctl copy",
            "description": "",
            "folder": str(domain_b.id),
            "duplicate_evidences": True,
        },
        format="json",
    )

    assert response.status_code == 403, response.content
    assert not AppliedControl.objects.filter(folder=domain_b).exists()


@pytest.mark.django_db
def test_applied_control_duplicate_cross_domain_with_rights_on_both(domains):
    domain_a, domain_b = domains
    client = _client_for(
        "dup-ana-ab@tests.com",
        [("BI-UG-ANA", domain_a), ("BI-UG-ANA", domain_b)],
    )
    control = AppliedControl.objects.create(name="ctl", folder=domain_a)

    response = client.post(
        f"/api/applied-controls/{control.id}/duplicate/",
        {
            "name": "ctl copy",
            "description": "",
            "folder": str(domain_b.id),
            "duplicate_evidences": False,
        },
        format="json",
    )

    assert response.status_code == 200, response.content
    assert AppliedControl.objects.filter(name="ctl copy", folder=domain_b).exists()


# --- risk assessments ---------------------------------------------------------


def _make_risk_assessment(folder):
    matrix = RiskMatrix.objects.create(
        name="3x3", folder=folder, json_definition=MATRIX_DEFINITION
    )
    perimeter = Perimeter.objects.create(name="perimeter", folder=folder)
    return RiskAssessment.objects.create(
        name="ra", folder=folder, perimeter=perimeter, risk_matrix=matrix
    )


@pytest.mark.django_db
def test_risk_assessment_duplicate_requires_rights_on_target_domain(domains):
    domain_a, domain_b = domains
    client = _client_for("dup-ana-a@tests.com", [("BI-UG-ANA", domain_a)])
    risk_assessment = _make_risk_assessment(domain_a)
    perimeter_b = Perimeter.objects.create(name="perimeter-b", folder=domain_b)

    response = client.post(
        f"/api/risk-assessments/{risk_assessment.id}/duplicate/",
        {
            "name": "ra copy",
            "description": "",
            "version": "1.0",
            "perimeter": str(perimeter_b.id),
            "folder": str(domain_b.id),
        },
        format="json",
    )

    assert response.status_code == 403, response.content
    assert not RiskAssessment.objects.filter(folder=domain_b).exists()


@pytest.mark.django_db
def test_risk_assessment_duplicate_folder_follows_perimeter(domains):
    domain_a, domain_b = domains
    client = _client_for(
        "dup-ana-ab@tests.com",
        [("BI-UG-ANA", domain_a), ("BI-UG-ANA", domain_b)],
    )
    risk_assessment = _make_risk_assessment(domain_a)
    perimeter_b = Perimeter.objects.create(name="perimeter-b", folder=domain_b)

    response = client.post(
        f"/api/risk-assessments/{risk_assessment.id}/duplicate/",
        {
            "name": "ra copy",
            "description": "",
            "version": "1.0",
            "perimeter": str(perimeter_b.id),
            # inconsistent on purpose: the perimeter's folder must win
            "folder": str(domain_a.id),
        },
        format="json",
    )

    assert response.status_code == 200, response.content
    duplicate = RiskAssessment.objects.get(name="ra copy")
    assert duplicate.folder == domain_b


@pytest.mark.django_db
def test_risk_assessment_duplicate_with_scenarios_requires_scenario_rights(domains):
    from iam.models import Permission, Role, RoleAssignment
    from core.models import RiskScenario

    domain_a, _ = domains
    user = User.objects.create_user("dup-ra-only@tests.com", is_published=True)
    user.folder = domain_a
    user.save()
    role = Role.objects.create(name="ra-only", folder=Folder.get_root_folder())
    role.permissions.set(
        Permission.objects.filter(
            codename__in=["view_riskassessment", "add_riskassessment"]
        )
    )
    assignment = RoleAssignment.objects.create(
        name="ra-only",
        user=user,
        role=role,
        folder=Folder.get_root_folder(),
        is_recursive=True,
    )
    assignment.perimeter_folders.add(domain_a)
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    risk_assessment = _make_risk_assessment(domain_a)
    payload = {
        "name": "ra copy",
        "description": "",
        "version": "1.0",
        "perimeter": str(risk_assessment.perimeter.id),
        "folder": str(domain_a.id),
    }

    # without scenarios, add_riskassessment alone is enough
    response = client.post(
        f"/api/risk-assessments/{risk_assessment.id}/duplicate/",
        payload,
        format="json",
    )
    assert response.status_code == 200, response.content

    RiskScenario.objects.create(
        name="scn", folder=domain_a, risk_assessment=risk_assessment
    )
    response = client.post(
        f"/api/risk-assessments/{risk_assessment.id}/duplicate/",
        {**payload, "name": "ra copy 2"},
        format="json",
    )
    assert response.status_code == 403, response.content
    assert not RiskAssessment.objects.filter(name="ra copy 2").exists()


# --- organisation objectives ---------------------------------------------------


@pytest.mark.django_db
def test_organisation_objective_duplicate_requires_rights_on_target_domain(domains):
    domain_a, domain_b = domains
    client = _client_for("dup-dma-a@tests.com", [("BI-UG-DMA", domain_a)])
    objective = OrganisationObjective.objects.create(name="obj", folder=domain_a)

    response = client.post(
        f"/api/organisation-objectives/{objective.id}/duplicate/",
        {"name": "obj copy", "description": "", "folder": str(domain_b.id)},
        format="json",
    )

    assert response.status_code == 403, response.content
    assert not OrganisationObjective.objects.filter(folder=domain_b).exists()


@pytest.mark.django_db
def test_organisation_objective_duplicate_same_domain(domains):
    domain_a, _ = domains
    client = _client_for("dup-dma-a@tests.com", [("BI-UG-DMA", domain_a)])
    objective = OrganisationObjective.objects.create(name="obj", folder=domain_a)

    response = client.post(
        f"/api/organisation-objectives/{objective.id}/duplicate/",
        {"name": "obj copy", "description": "", "folder": str(domain_a.id)},
        format="json",
    )

    assert response.status_code == 200, response.content
    assert OrganisationObjective.objects.filter(
        name="obj copy", folder=domain_a
    ).exists()
