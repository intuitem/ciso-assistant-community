import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from integrations.models import IntegrationConfiguration, IntegrationProvider

URL = "/api/settings/general/object/"
SECRET = "VictimSecret"


@pytest.fixture
def app_ready(db):
    startup(sender=None)
    return Folder.get_root_folder()


@pytest.fixture
def victim_config(app_ready):
    folder = Folder.objects.create(
        name="VictimDom",
        parent_folder=app_ready,
        content_type=Folder.ContentType.DOMAIN,
    )
    provider, _ = IntegrationProvider.objects.get_or_create(
        name="servicenow", defaults={"provider_type": "itsm", "is_active": True}
    )
    provider.is_active = True
    provider.save()
    return IntegrationConfiguration.objects.create(
        provider=provider,
        folder=folder,
        is_active=True,
        credentials={"instance_url": "https://victim.example", "password": SECRET},
        settings={},
    )


def _client(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def norole_client(app_ready):
    user = User.objects.create_user("norole@gs.test", is_published=True)
    user.folder = app_ready
    user.save()
    return _client(user)


@pytest.fixture
def admin_client(app_ready):
    user = User.objects.create_user("admin@gs.test", is_published=True)
    group = UserGroup.objects.get(name="BI-UG-ADM", folder=app_ready)
    user.folder = group.folder
    user.save()
    group.user_set.add(user)
    return _client(user)


def _integrations(resp):
    return resp.json().get("enabled_integrations", [])


def test_user_without_role_sees_no_configuration_ids(norole_client, victim_config):
    resp = norole_client.get(URL)
    assert resp.status_code == 200
    assert str(victim_config.id) not in resp.content.decode()
    assert SECRET not in resp.content.decode()
    # The frontend gates ITSM features on `configurations?.length`.
    for integration in _integrations(resp):
        assert integration["configurations"] == []


def test_admin_still_sees_the_configuration(admin_client, victim_config):
    resp = admin_client.get(URL)
    assert resp.status_code == 200
    servicenow = [i for i in _integrations(resp) if i["name"] == "servicenow"]
    assert servicenow, "provider must still be listed"
    assert str(victim_config.id) in servicenow[0]["configurations"]


def test_domain_scoped_user_sees_only_their_own(app_ready, victim_config):
    own_folder = Folder.objects.create(
        name="OwnDom", parent_folder=app_ready, content_type=Folder.ContentType.DOMAIN
    )
    own_config = IntegrationConfiguration.objects.create(
        provider=victim_config.provider,
        folder=own_folder,
        is_active=True,
        credentials={"instance_url": "https://own.example"},
        settings={},
    )
    user = User.objects.create_user("dma@gs.test", is_published=True)
    user.folder = app_ready
    user.save()
    group = UserGroup.objects.create(name="grp-dma", folder=own_folder)
    group.user_set.add(user)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name="BI-RL-DMA"),
        folder=own_folder,
        is_recursive=True,
    )
    assignment.perimeter_folders.add(own_folder)

    resp = _client(user).get(URL)
    body = resp.content.decode()
    assert str(own_config.id) in body
    assert str(victim_config.id) not in body
