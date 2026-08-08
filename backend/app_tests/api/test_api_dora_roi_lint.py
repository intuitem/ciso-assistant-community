import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import Asset
from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from tprm.models import Entity

URL = "/api/entities/dora_roi_lint/"


@pytest.fixture
def app_ready(db):
    startup(sender=None)
    return Folder.get_root_folder()


@pytest.fixture
def victim_folder(app_ready):
    folder = Folder.objects.create(
        name="Victim", parent_folder=app_ready, content_type=Folder.ContentType.DOMAIN
    )
    Entity.objects.create(name="CANARY-SUPPLIER", folder=folder)
    Asset.objects.create(
        name="CANARY-BUSINESS-FUNCTION", folder=folder, is_business_function=True
    )
    return folder


def _client(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _global_group_client(email, group_name, app_ready):
    user = User.objects.create_user(email, is_published=True)
    group = UserGroup.objects.get(name=group_name, folder=app_ready)
    user.folder = group.folder
    user.save()
    group.user_set.add(user)
    return _client(user)


@pytest.fixture
def norole_client(app_ready):
    user = User.objects.create_user("norole@dora.test", is_published=True)
    user.folder = app_ready
    user.save()
    return _client(user)


@pytest.fixture
def admin_client(app_ready):
    return _global_group_client("admin@dora.test", "BI-UG-ADM", app_ready)


@pytest.fixture
def global_reader_client(app_ready):
    return _global_group_client("reader@dora.test", "BI-UG-GAD", app_ready)


@pytest.fixture
def domain_analyst_client(app_ready, victim_folder):
    user = User.objects.create_user("analyst@dora.test", is_published=True)
    user.folder = app_ready
    user.save()
    group = UserGroup.objects.create(name="domain-analysts", folder=victim_folder)
    group.user_set.add(user)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name="BI-RL-ANA"),
        folder=victim_folder,
        is_recursive=True,
    )
    assignment.perimeter_folders.add(victim_folder)
    return _client(user)


def test_user_without_role_is_denied(norole_client, victim_folder):
    resp = norole_client.get(URL)
    assert resp.status_code == 403
    assert "CANARY-BUSINESS-FUNCTION" not in resp.content.decode()


def test_domain_scoped_analyst_is_denied(domain_analyst_client, victim_folder):
    resp = domain_analyst_client.get(URL)
    assert resp.status_code == 403
    assert "CANARY-BUSINESS-FUNCTION" not in resp.content.decode()


def test_admin_is_allowed(admin_client, victim_folder):
    resp = admin_client.get(URL)
    assert resp.status_code == 200
    assert "CANARY-BUSINESS-FUNCTION" in resp.content.decode()


def test_global_reader_is_allowed(global_reader_client, victim_folder):
    assert global_reader_client.get(URL).status_code == 200
