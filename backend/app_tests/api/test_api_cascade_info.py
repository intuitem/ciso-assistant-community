import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import Asset
from iam.models import Folder, Role, RoleAssignment, User, UserGroup


@pytest.fixture
def app_ready(db):
    startup(sender=None)
    return Folder.get_root_folder()


def _client(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def target_folder(app_ready):
    folder = Folder.objects.create(
        name="Target", parent_folder=app_ready, content_type=Folder.ContentType.DOMAIN
    )
    Asset.objects.create(name="CANARY-ASSET", folder=folder)
    return folder


def _scoped_client(email, role_name, folder, app_ready):
    user = User.objects.create_user(email, is_published=True)
    user.folder = app_ready
    user.save()
    group = UserGroup.objects.create(name=f"grp-{email}", folder=folder)
    group.user_set.add(user)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=role_name),
        folder=folder,
        is_recursive=True,
    )
    assignment.perimeter_folders.add(folder)
    return _client(user)


@pytest.fixture
def admin_client(app_ready):
    user = User.objects.create_user("admin@cascade.test", is_published=True)
    group = UserGroup.objects.get(name="BI-UG-ADM", folder=app_ready)
    user.folder = group.folder
    user.save()
    group.user_set.add(user)
    return _client(user)


def _url(folder):
    return f"/api/folders/{folder.id}/cascade-info/"


# Roles that hold view_folder but not delete_folder
@pytest.mark.parametrize(
    "role_name",
    ["BI-RL-AUD", "BI-RL-ANA", "BI-RL-APP", "BI-RL-ADE", "BI-RL-TPR", "BI-RL-TST"],
)
def test_view_only_roles_are_denied(app_ready, target_folder, role_name):
    client = _scoped_client(
        f"{role_name}@cascade.test", role_name, target_folder, app_ready
    )
    resp = client.get(_url(target_folder))
    assert resp.status_code == 403
    assert "CANARY-ASSET" not in resp.content.decode()


def test_user_without_role_is_denied(app_ready, target_folder):
    user = User.objects.create_user("norole@cascade.test", is_published=True)
    user.folder = app_ready
    user.save()
    resp = _client(user).get(_url(target_folder))
    assert resp.status_code in (403, 404)


def test_domain_manager_is_allowed(app_ready, target_folder):
    client = _scoped_client("dma@cascade.test", "BI-RL-DMA", target_folder, app_ready)
    resp = client.get(_url(target_folder))
    assert resp.status_code == 200
    assert "CANARY-ASSET" in resp.content.decode()


def test_admin_is_allowed(admin_client, target_folder):
    resp = admin_client.get(_url(target_folder))
    assert resp.status_code == 200
    assert "CANARY-ASSET" in resp.content.decode()


def test_cross_folder_m2m_endpoint_is_not_disclosed(app_ready, target_folder):
    # An M2M link reaching out of the deleted subtree bubbles both endpoints,
    # so the far object must be filtered out unless independently viewable.
    secret = Folder.objects.create(
        name="Secret", parent_folder=app_ready, content_type=Folder.ContentType.DOMAIN
    )
    hidden_parent = Asset.objects.create(name="SECRET-PARENT-ASSET", folder=secret)
    child = Asset.objects.create(name="my-child", folder=target_folder)
    child.parent_assets.add(hidden_parent)

    client = _scoped_client("dma2@cascade.test", "BI-RL-DMA", target_folder, app_ready)
    resp = client.get(_url(target_folder))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "my-child" in body
    assert "SECRET-PARENT-ASSET" not in body
    assert str(hidden_parent.id) not in body


def test_role_assignment_emails_not_leaked_to_view_only_role(app_ready, target_folder):
    victim = User.objects.create_user("victim@cascade.test", is_published=True)
    victim.folder = app_ready
    victim.save()
    group = UserGroup.objects.create(name="victim-grp", folder=target_folder)
    group.user_set.add(victim)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name="BI-RL-DMA"),
        folder=target_folder,
        is_recursive=True,
    )
    assignment.perimeter_folders.add(target_folder)

    client = _scoped_client(
        "auditee@cascade.test", "BI-RL-ADE", target_folder, app_ready
    )
    resp = client.get(_url(target_folder))
    assert resp.status_code == 403
    assert "victim@cascade.test" not in resp.content.decode()
