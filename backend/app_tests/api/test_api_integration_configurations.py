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


# The provider link skips the visibility check, so the field's own queryset is
# its only gate.
def test_inactive_provider_cannot_be_linked_on_create(
    admin_client, root_folder, jira_provider
):
    jira_provider.is_active = False
    jira_provider.save()

    response = admin_client.post(
        CONFIGS_URL, _create_payload(root_folder, jira_provider), format="json"
    )

    assert response.status_code == 400, response.content
    assert "provider_id" in response.json()
    assert not IntegrationConfiguration.objects.exists()


def test_inactive_provider_cannot_be_linked_on_update(
    admin_client, root_folder, jira_config
):
    servicenow = IntegrationProvider.objects.get(name="servicenow")
    servicenow.is_active = False
    servicenow.save()

    response = admin_client.patch(
        f"{CONFIGS_URL}{jira_config.id}/",
        {"provider_id": str(servicenow.id)},
        format="json",
    )

    assert response.status_code == 400, response.content
    assert "provider_id" in response.json()
    jira_config.refresh_from_db()
    assert jira_config.provider.name == "jira"


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


def test_glpi_item_type_is_locked_while_objects_are_linked(admin_client, root_folder):
    from django.contrib.contenttypes.models import ContentType

    from core.models import AppliedControl
    from integrations.models import SyncMapping

    config = IntegrationConfiguration.objects.create(
        provider=IntegrationProvider.objects.get(name="glpi"),
        folder=root_folder,
        credentials={
            "instance_url": "https://glpi.example.com",
            "client_id": "cid",
            "client_secret": "csecret",
            "username": "sync",
            "password": "pw",
        },
        settings={"table_name": "Ticket"},
    )
    url = f"{CONFIGS_URL}{config.id}/"

    # What the settings form sends: the secrets stay on the server.
    shown = {
        "instance_url": "https://glpi.example.com",
        "client_id": "cid",
        "username": "sync",
    }

    def save(**settings):
        return admin_client.patch(
            url, {"credentials": shown, "settings": settings}, format="json"
        )

    # Nothing linked yet: the type is free to change.
    assert save(table_name="Change").status_code == 200
    assert save(table_name="Ticket").status_code == 200

    control = AppliedControl.objects.create(name="Linked", folder=root_folder)
    SyncMapping.objects.create(
        configuration=config,
        content_type=ContentType.objects.get_for_model(AppliedControl),
        local_object_id=control.id,
        remote_id="7",
    )

    response = save(table_name="Change")
    assert response.status_code == 400, response.content
    assert "Ticket to Change" in str(response.json())
    config.refresh_from_db()
    assert config.settings["table_name"] == "Ticket"

    # Other settings still save, and so does the same type.
    response = save(table_name="Ticket", enable_outgoing_sync=True)
    assert response.status_code == 200, response.content


def test_glpi_refuses_settings_for_other_models(admin_client, root_folder):
    credentials = {
        "instance_url": "https://glpi.example.com",
        "client_id": "cid",
        "client_secret": "csecret",
        "username": "sync",
        "password": "pw",
    }
    payload = {
        "provider_id": str(IntegrationProvider.objects.get(name="glpi").id),
        "folder_id": str(root_folder.id),
        "credentials": credentials,
        "settings": {
            "table_name": "Ticket",
            "models": {"asset": {"table_name": "Ticket"}},
        },
    }

    response = admin_client.post(CONFIGS_URL, payload, format="json")
    assert response.status_code == 400, response.content
    assert "asset" in str(response.json())

    payload["settings"] = {"table_name": "Ticket"}
    created = admin_client.post(CONFIGS_URL, payload, format="json")
    assert created.status_code == 201, created.content

    response = admin_client.patch(
        f"{CONFIGS_URL}{created.json()['id']}/",
        {
            "credentials": credentials,
            "settings": {"models": {"asset": {"table_name": "Ticket"}}},
        },
        format="json",
    )
    assert response.status_code == 400, response.content


def test_glpi_cannot_be_linked_to_objects_it_does_not_sync(admin_client, root_folder):
    from core.models import Asset
    from integrations.models import SyncMapping

    config = IntegrationConfiguration.objects.create(
        provider=IntegrationProvider.objects.get(name="glpi"),
        folder=root_folder,
        credentials={
            "instance_url": "https://glpi.example.com",
            "client_id": "cid",
            "client_secret": "csecret",
            "username": "sync",
            "password": "pw",
        },
        settings={"table_name": "Ticket"},
    )
    asset = Asset.objects.create(name="Server", folder=root_folder)

    response = admin_client.patch(
        f"/api/assets/{asset.id}/",
        {"integration_config": str(config.id), "remote_object_id": "7"},
        format="json",
    )
    assert response.status_code == 400, response.content
    assert "integration_config" in response.json()
    assert not SyncMapping.objects.filter(configuration=config).exists()

    with patch("integrations.views.IntegrationRegistry.get_client") as get_client:
        response = admin_client.get(
            f"{CONFIGS_URL}{config.id}/remote-objects/", {"model_key": "asset"}
        )
    assert response.status_code == 400, response.content
    get_client.assert_not_called()


@pytest.mark.parametrize(
    "provider, credentials, host_key, secret_key",
    [
        ("jira", JIRA_CREDENTIALS, "server_url", "api_token"),
        (
            "servicenow",
            {
                "instance_url": "https://example.service-now.com",
                "username": "sync",
                "password": "pw",
            },
            "instance_url",
            "password",
        ),
    ],
)
def test_saved_secret_stays_with_its_connection(
    admin_client, root_folder, provider, credentials, host_key, secret_key
):
    config = IntegrationConfiguration.objects.create(
        provider=IntegrationProvider.objects.get(name=provider),
        folder=root_folder,
        credentials=dict(credentials),
        settings={"table_name": "incident"},
    )
    url = f"{CONFIGS_URL}{config.id}/"
    shown = {k: v for k, v in credentials.items() if k != secret_key}

    def save(**changes):
        return admin_client.patch(
            url,
            {"credentials": {**shown, **changes}, "settings": config.settings},
            format="json",
        )

    # What the settings page sends when nothing about the connection changed.
    assert save().status_code == 200

    response = save(**{host_key: "https://elsewhere.example"})
    assert response.status_code == 400, response.content
    assert "credentials" in response.json()
    config.refresh_from_db()
    assert config.credentials == credentials

    moved = {host_key: "https://elsewhere.example", secret_key: "new-secret"}
    assert save(**moved).status_code == 200
    config.refresh_from_db()
    assert config.credentials == {**credentials, **moved}


def test_glpi_saved_secrets_stay_with_their_connection(admin_client, root_folder):
    stored = {
        "instance_url": "https://glpi.example.com",
        "client_id": "cid",
        "client_secret": "csecret",
        "username": "sync",
        "password": "pw",
    }
    config = IntegrationConfiguration.objects.create(
        provider=IntegrationProvider.objects.get(name="glpi"),
        folder=root_folder,
        credentials=dict(stored),
        settings={"table_name": "Ticket"},
    )
    url = f"{CONFIGS_URL}{config.id}/"
    shown = {k: stored[k] for k in ("instance_url", "client_id", "username")}

    def save(**changes):
        return admin_client.patch(
            url,
            {"credentials": {**shown, **changes}, "settings": config.settings},
            format="json",
        )

    assert save().status_code == 200
    elsewhere = {"instance_url": "https://elsewhere.example"}
    # Fresh values for the two secret keys, derived so that no literal here
    # looks like a credential to a secret scanner.
    fresh = {key: f"{stored[key]}-rotated" for key in ("client_secret", "password")}

    # Neither secret, then only one of the two: the other would follow along.
    assert save(**elsewhere).status_code == 400
    assert save(**elsewhere, password=fresh["password"]).status_code == 400
    config.refresh_from_db()
    assert config.credentials == stored

    moved = {**elsewhere, **fresh}
    assert save(**moved).status_code == 200
    config.refresh_from_db()
    assert config.credentials == {**stored, **moved}
