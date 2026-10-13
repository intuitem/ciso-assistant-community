import pytest
from django.contrib.auth.models import Permission
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.models import Incident
from core.startup import startup
from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from privacy.models import DataBreach

URL = "/api/privacy/data-breaches/"


@pytest.fixture
def domain():
    startup(sender=None)
    return Folder.objects.create(
        name="BreachDomain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )


@pytest.fixture
def admin_client(domain):
    admin = User.objects.create_superuser("admin@breach-tests.local")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    _, token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _breach(domain, **extra):
    return {
        "name": "Lost laptop",
        "folder": str(domain.id),
        "discovered_on": "2026-10-13T09:00:00Z",
        "breach_type": "privacy_loss",
        "risk_level": "privacy_risk",
        "status": "privacy_discovered",
        **extra,
    }


@pytest.mark.django_db
def test_typed_name_creates_then_reuses_an_incident(admin_client, domain):
    res = admin_client.post(
        URL, _breach(domain, incident="Laptop theft"), format="json"
    )
    assert res.status_code == 201, res.content
    incident = DataBreach.objects.get().incident
    assert incident.name == "Laptop theft"
    assert incident.folder == domain

    res = admin_client.post(
        URL, _breach(domain, name="Second", incident="Laptop theft"), format="json"
    )
    assert res.status_code == 201, res.content
    assert Incident.objects.filter(name="Laptop theft").count() == 1


@pytest.mark.django_db
def test_failed_breach_write_leaves_no_incident(admin_client, domain):
    res = admin_client.post(
        URL, _breach(domain, incident="Orphan", breach_type="bogus"), format="json"
    )
    assert res.status_code == 400, res.content
    assert not Incident.objects.filter(name="Orphan").exists()


@pytest.mark.django_db
def test_no_incident_without_the_right_to_add_one(domain):
    user = User.objects.create_user(email="breach@test.local", is_published=True)
    role = Role.objects.create(name="BreachRole", folder=domain)
    role.permissions.set(
        Permission.objects.filter(
            codename__in=[
                "view_folder",
                "add_databreach",
                "view_databreach",
                "view_incident",
            ]
        )
    )
    group = UserGroup.objects.create(name="BreachGroup", folder=domain)
    group.user_set.add(user)
    assignment = RoleAssignment.objects.create(
        user_group=group, role=role, folder=domain, is_recursive=True
    )
    assignment.perimeter_folders.add(domain)
    client = APIClient()
    client.force_authenticate(user=user)

    res = client.post(URL, _breach(domain, incident="Laptop theft"), format="json")
    assert res.status_code == 403, res.content
    assert not Incident.objects.exists()
    assert not DataBreach.objects.exists()
