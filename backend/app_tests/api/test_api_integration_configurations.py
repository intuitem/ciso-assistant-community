"""Integration configurations through the real API stack: creating one, and the
remote object picker. Requests go through routing, the filter backends and
permissions, so the tests see what the viewset does with the picker's
parameters. Only the remote system is stubbed."""

from unittest.mock import MagicMock, patch

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from iam.models import Folder, User, UserGroup
from integrations.models import IntegrationConfiguration, IntegrationProvider

CONFIGS_URL = "/api/integrations/configs/"
JIRA_CREDENTIALS = {
    "server_url": "https://example.atlassian.net",
    "email": "sync@example.com",
    "api_token": "token",
}


@pytest.fixture
def root_folder(db):
    startup(sender=None)
    return Folder.get_root_folder()


@pytest.fixture
def jira_provider(root_folder):
    return IntegrationProvider.objects.get(name="jira")


def _client(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def admin_client(root_folder):
    user = User.objects.create_user("admin@integrations.test")
    group = UserGroup.objects.get(name="BI-UG-ADM", folder=root_folder)
    user.folder = group.folder
    user.save()
    group.user_set.add(user)
    return _client(user)


@pytest.fixture
def norole_client(root_folder):
    user = User.objects.create_user("norole@integrations.test")
    user.folder = root_folder
    user.save()
    return _client(user)


@pytest.fixture
def jira_config(root_folder, jira_provider):
    return IntegrationConfiguration.objects.create(
        provider=jira_provider,
        folder=root_folder,
        credentials=dict(JIRA_CREDENTIALS),
        settings={"table_name": "PROJ:Task"},
    )


def _create_payload(root_folder, provider):
    return {
        "provider_id": str(provider.id),
        "folder_id": str(root_folder.id),
        "credentials": JIRA_CREDENTIALS,
        "settings": {"table_name": "PROJ:Task"},
    }


def test_admin_can_create_a_configuration(admin_client, root_folder, jira_provider):
    response = admin_client.post(
        CONFIGS_URL, _create_payload(root_folder, jira_provider), format="json"
    )

    assert response.status_code == 201, response.content
    config = IntegrationConfiguration.objects.get(pk=response.json()["id"])
    assert config.provider == jira_provider


def test_user_without_role_cannot_create_a_configuration(
    norole_client, root_folder, jira_provider
):
    response = norole_client.post(
        CONFIGS_URL, _create_payload(root_folder, jira_provider), format="json"
    )

    # Refused on the folder, which is not selectable without access to it.
    assert response.status_code == 400, response.content
    assert "folder_id" in response.json()
    assert not IntegrationConfiguration.objects.exists()


def test_configurations_can_be_searched_by_provider(admin_client, jira_config):
    response = admin_client.get(CONFIGS_URL, {"search": "jira"})
    assert response.status_code == 200
    assert [c["id"] for c in response.json()["results"]] == [str(jira_config.id)]

    response = admin_client.get(CONFIGS_URL, {"search": "servicenow"})
    assert response.status_code == 200
    assert response.json()["results"] == []


def _list_remote_objects(client, config, query, path="remote-objects/"):
    remote = MagicMock()
    remote.list_remote_objects.return_value = [{"id": "PROJ-1"}]
    with patch("integrations.views.IntegrationRegistry.get_client") as get_client:
        get_client.return_value = remote
        response = client.get(f"{CONFIGS_URL}{config.id}/{path}", query)
    return response, remote


@pytest.mark.parametrize("path", ["remote-objects/", "remote-objects/autocomplete/"])
def test_picker_search_goes_to_the_remote_system(admin_client, jira_config, path):
    response, remote = _list_remote_objects(
        admin_client, jira_config, {"search": "firewall"}, path
    )

    assert response.status_code == 200, response.content
    assert response.json() == [{"id": "PROJ-1"}]
    assert remote.list_remote_objects.call_args[1]["query_params"] == {
        "search": "firewall",
        "id": "",
        "limit": 50,
    }


@pytest.mark.parametrize(
    "remote_ids",
    [
        "PROJ-7,PROJ-8",  # Jira keys
        "7,8",  # numeric ids
        "6816f79cc0a8016401c5a33be04be441",  # ServiceNow sys_id: parses as a UUID
    ],
)
def test_picker_hydration_ids_are_remote_ids(admin_client, jira_config, remote_ids):
    response, remote = _list_remote_objects(
        admin_client, jira_config, {"id": remote_ids}
    )

    assert response.status_code == 200, response.content
    assert remote.list_remote_objects.call_args[1]["query_params"]["id"] == remote_ids


def test_picker_limit_is_clamped_and_defaulted(admin_client, jira_config):
    cases = [
        ({"limit": "20"}, 20),
        ({"limit": "5000"}, 100),
        ({"limit": "0"}, 1),
        ({"limit": "abc"}, 50),
        ({}, 50),
    ]
    for query, expected in cases:
        response, remote = _list_remote_objects(admin_client, jira_config, query)

        assert response.status_code == 200, response.content
        sent = remote.list_remote_objects.call_args[1]["query_params"]
        assert sent["limit"] == expected, query


def test_picker_rejects_an_unknown_model_key(admin_client, jira_config):
    response, remote = _list_remote_objects(
        admin_client, jira_config, {"model_key": "nonsense"}
    )

    assert response.status_code == 400
    remote.list_remote_objects.assert_not_called()


def test_picker_stays_closed_without_access_to_the_configuration(
    norole_client, jira_config
):
    response, remote = _list_remote_objects(
        norole_client, jira_config, {"search": "firewall"}
    )

    assert response.status_code == 404
    remote.list_remote_objects.assert_not_called()
