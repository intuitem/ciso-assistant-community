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

    from core.models import AppliedControl, Asset
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
        remote_id="Ticket:7",
    )

    response = save(table_name="Change")
    assert response.status_code == 400, response.content
    assert "Ticket to Change" in str(response.json())
    config.refresh_from_db()
    assert config.settings["table_name"] == "Ticket"

    # Other settings still save, and so does the same type.
    response = save(table_name="Ticket", enable_outgoing_sync=True)
    assert response.status_code == 200, response.content

    # Each model has its own lock: a linked control does not hold the asset
    # type, which is free until an asset is linked.
    def save_assets(item_type):
        return save(table_name="Ticket", models={"asset": {"table_name": item_type}})

    assert save_assets("Computer").status_code == 200
    assert save_assets("Software").status_code == 200

    asset = Asset.objects.create(name="Linked", folder=root_folder)
    SyncMapping.objects.create(
        configuration=config,
        content_type=ContentType.objects.get_for_model(Asset),
        local_object_id=asset.id,
        remote_id="Software:7",
    )

    response = save_assets("Computer")
    assert response.status_code == 400, response.content
    assert "Software to Computer" in str(response.json())
    assert save_assets("Software").status_code == 200
    # Turning asset sync off is not a change of type, and does not free it:
    # the links still name software.
    assert save_assets("").status_code == 200
    response = save_assets("Computer")
    assert response.status_code == 400, response.content
    assert "Software to Computer" in str(response.json())
    assert save_assets("Software").status_code == 200


GLPI_SHOWN_CREDENTIALS = {
    "instance_url": "https://glpi.example.com",
    "client_id": "cid",
    "username": "sync",
}
GLPI_CREDENTIALS = {
    **GLPI_SHOWN_CREDENTIALS,
    "client_secret": "csecret",
    "password": "pw",
}


def test_glpi_checks_the_settings_of_each_model(admin_client, root_folder):
    payload = {
        "provider_id": str(IntegrationProvider.objects.get(name="glpi").id),
        "folder_id": str(root_folder.id),
        "credentials": GLPI_CREDENTIALS,
        "settings": {
            "table_name": "Ticket",
            "models": {"asset": {"table_name": "Ticket"}},
        },
    }

    # A ticket is not an asset type.
    response = admin_client.post(CONFIGS_URL, payload, format="json")
    assert response.status_code == 400, response.content
    assert "asset" in str(response.json())

    payload["settings"]["models"] = {"finding": {"table_name": "Ticket"}}
    response = admin_client.post(CONFIGS_URL, payload, format="json")
    assert response.status_code == 400, response.content
    assert "finding" in str(response.json())

    payload["settings"] = {"table_name": "Ticket"}
    created = admin_client.post(CONFIGS_URL, payload, format="json")
    assert created.status_code == 201, created.content
    url = f"{CONFIGS_URL}{created.json()['id']}/"

    def save(asset_settings):
        settings = {"table_name": "Ticket", "models": {"asset": asset_settings}}
        return admin_client.patch(
            url,
            {"credentials": GLPI_SHOWN_CREDENTIALS, "settings": settings},
            format="json",
        )

    assert save({"table_name": "Ticket"}).status_code == 400
    assert save({"table_name": "Computer", "field_map": ["name"]}).status_code == 400
    response = save({"table_name": "Computer", "field_map": {"name": "name"}})
    assert response.status_code == 200, response.content
    stored = IntegrationConfiguration.objects.get(pk=created.json()["id"]).settings
    assert stored["models"]["asset"]["table_name"] == "Computer"


class FakeGLPI:
    """Stands in for the GLPI client's item calls: items live in ``items``,
    keyed by item type and id, and every write is recorded."""

    def __init__(self):
        self.items: dict[tuple[str, str], dict] = {}
        self.writes: list[tuple[str, str, dict]] = []
        self.clock = 0

    def put(self, item_type, item_id, **fields):
        item = self.items.setdefault((item_type, str(item_id)), {"id": int(item_id)})
        item.update(fields)
        self.clock += 1
        item["date_mod"] = f"2026-11-20T10:00:{self.clock:02d}+00:00"

    def _read(self, client, remote_id):
        item = self.items.get((client.table, client._item_id(remote_id)))
        return None if item is None else client.normalize_item(dict(item))

    def _get(self, client, remote_id):
        return self._read(client, remote_id)

    def _update(self, client, remote_id, changes):
        item_id = client._item_id(remote_id)
        self.writes.append((client.table, item_id, dict(changes)))
        self.put(client.table, item_id, **changes)
        return True

    def _create(self, client, local_object):
        raise AssertionError("no item is expected to be created")

    def __enter__(self):
        from contextlib import ExitStack

        from integrations.itsm.glpi.client import GLPIClient

        self._stack = ExitStack()
        self._stack.enter_context(
            patch("integrations.itsm.glpi.client.check_integration_url")
        )
        for method, fake in (
            ("read_item", self._read),
            ("get_remote_object", self._get),
            ("update_remote_object", self._update),
            ("create_remote_object", self._create),
        ):
            self._stack.enter_context(
                patch.object(GLPIClient, method, autospec=True, side_effect=fake)
            )
        return self

    def __exit__(self, *exc):
        self._stack.close()


def _glpi_config(root_folder, **settings):
    return IntegrationConfiguration.objects.create(
        provider=IntegrationProvider.objects.get(name="glpi"),
        folder=root_folder,
        credentials=GLPI_CREDENTIALS,
        settings={"table_name": "Ticket", **settings},
    )


COMPUTERS = {"asset": {"table_name": "Computer", "field_map": {"name": "name"}}}


def _orchestrator(config):
    from integrations.registry import IntegrationRegistry

    config.refresh_from_db()
    return IntegrationRegistry.get_orchestrator(config)


def _link(config, local_object, remote_id, **fields):
    from django.contrib.contenttypes.models import ContentType

    from integrations.models import SyncMapping

    return SyncMapping.objects.create(
        configuration=config,
        content_type=ContentType.objects.get_for_model(local_object),
        local_object_id=local_object.id,
        remote_id=remote_id,
        **fields,
    )


def test_glpi_ticket_and_asset_sharing_an_id_sync_apart(admin_client, root_folder):
    """GLPI numbers each item type on its own, and a webhook does not name
    the type it is about: ticket 4 and computer 4 must not be mixed up."""
    from core.models import AppliedControl, Asset
    from integrations.models import SyncMapping

    config = _glpi_config(root_folder, models=COMPUTERS)
    control = AppliedControl.objects.create(name="Control", folder=root_folder)
    asset = Asset.objects.create(name="Asset", folder=root_folder)

    # Linked through the API with the id GLPI shows.
    with patch("core.views.sync_object_to_integrations"):
        for url in (f"/api/applied-controls/{control.id}/", f"/api/assets/{asset.id}/"):
            response = admin_client.patch(
                url,
                {"integration_config": str(config.id), "remote_object_id": "4"},
                format="json",
            )
            assert response.status_code == 200, response.content

    def links():
        return {
            mapping.content_type.model: mapping
            for mapping in SyncMapping.objects.filter(configuration=config)
        }

    def names():
        control.refresh_from_db()
        asset.refresh_from_db()
        return control.name, asset.name

    with FakeGLPI() as glpi:
        glpi.put("Ticket", 4, name="Ticket 4")
        glpi.put("Computer", 4, name="Computer 4")

        # The push queued by the link stores each id under its item type. A
        # link copies nothing either way.
        orchestrator = _orchestrator(config)
        assert orchestrator.push_changes(control, []) is True
        assert orchestrator.push_changes(asset, []) is True
        assert links()["appliedcontrol"].remote_id == "Ticket:4"
        assert links()["asset"].remote_id == "Computer:4"
        assert glpi.writes == []
        assert names() == ("Control", "Asset")

        # The computer is renamed in GLPI. The delivery only says "item 4":
        # the asset follows, the control linked to ticket 4 is left alone.
        glpi.put("Computer", 4, name="Computer 4 renamed")
        update = {"item": {"id": 4}}
        assert _orchestrator(config).handle_webhook_event("update", update) is True
        assert names() == ("Control", "Computer 4 renamed")

        # And the other way round.
        glpi.put("Ticket", 4, name="Ticket 4 renamed")
        assert _orchestrator(config).handle_webhook_event("update", update) is True
        assert names() == ("Ticket 4 renamed", "Computer 4 renamed")

        # The computer is deleted in GLPI: the ticket link is left alone.
        del glpi.items[("Computer", "4")]
        assert _orchestrator(config).handle_webhook_event("delete", update) is True
        assert links()["asset"].sync_status == SyncMapping.SyncStatus.FAILED
        assert links()["appliedcontrol"].sync_status == SyncMapping.SyncStatus.SYNCED

        # Items nobody linked are not read.
        glpi.put("Ticket", 5, name="Unlinked")
        other = {"item": {"id": 5}}
        assert _orchestrator(config).handle_webhook_event("update", other) is False


def test_glpi_bare_id_link_syncs_with_outgoing_sync_off(root_folder):
    """Nothing is pushed then, so the id stays as the API call gave it until
    the first delivery about it."""
    from core.models import AppliedControl, Asset

    config = _glpi_config(root_folder, models=COMPUTERS, enable_incoming_sync=True)
    asset = Asset.objects.create(name="Asset", folder=root_folder)
    control = AppliedControl.objects.create(name="Control", folder=root_folder)
    asset_link = _link(config, asset, "4")
    # Linked under an asset type by mistake: a control is never synced with a
    # computer.
    control_link = _link(config, control, "Computer:7")

    with FakeGLPI() as glpi:
        glpi.put("Computer", 4, name="Computer 4")
        glpi.put("Computer", 7, name="Computer 7")
        glpi.put("Ticket", 7, name="Ticket 7")
        orchestrator = _orchestrator(config)
        assert orchestrator.handle_webhook_event("update", {"item": {"id": 4}}) is True
        assert orchestrator.handle_webhook_event("update", {"item": {"id": 7}}) is False

    asset_link.refresh_from_db()
    asset.refresh_from_db()
    control.refresh_from_db()
    control_link.refresh_from_db()
    assert asset_link.remote_id == "Computer:4"
    assert asset.name == "Computer 4"
    assert control.name == "Control"
    assert control_link.remote_data == {}


def test_glpi_relinked_object_takes_the_first_update_of_its_new_item(root_folder):
    from core.models import Asset

    config = _glpi_config(root_folder, models=COMPUTERS, enable_incoming_sync=True)
    asset = Asset.objects.create(name="Asset", folder=root_folder)
    # Was linked to computer 4, read at 16:05, then pointed at computer 5.
    link = _link(
        config,
        asset,
        "Computer:5",
        remote_data={
            "key": "4",
            "fields": {"id": 4, "name": "Computer 4"},
            "updated": "2026-11-20T16:05:00+00:00",
        },
    )

    with FakeGLPI() as glpi:
        glpi.put("Computer", 5, name="Computer 5")
        glpi.items[("Computer", "5")]["date_mod"] = "2026-11-20T16:02:00+00:00"
        update = {"item": {"id": 5}}
        assert _orchestrator(config).handle_webhook_event("update", update) is True

    asset.refresh_from_db()
    link.refresh_from_db()
    assert asset.name == "Computer 5"
    assert link.remote_data["key"] == "5"


def test_glpi_pending_local_edit_and_glpi_change_both_survive(root_folder):
    """A rename waits to be pushed while GLPI changes the priority, and the
    delivery comes twice. Then the other order: the push runs first, and its
    read-back already holds a GLPI change nobody applied yet."""
    from core.models import AppliedControl

    config = _glpi_config(root_folder, enable_incoming_sync=True)
    control = AppliedControl.objects.create(
        name="Old name", priority=3, folder=root_folder
    )
    link = _link(config, control, "Ticket:4")
    update = {"item": {"id": 4}}

    with FakeGLPI() as glpi:
        glpi.put("Ticket", 4, name="Old name", priority=3, status={"id": 1})
        assert _orchestrator(config).push_changes(control, []) is True

        # Renamed locally, not pushed yet. GLPI raises the priority.
        control.name = "Renamed locally"
        control.save(skip_sync=True)
        glpi.put("Ticket", 4, priority=5)
        for _ in range(2):
            assert _orchestrator(config).handle_webhook_event("update", update) is True
            control.refresh_from_db()
            assert (control.name, control.priority) == ("Renamed locally", 1)

        # The rename is pushed. Meanwhile GLPI lowered the priority again:
        # the push reads that back, and the delivery about it comes after.
        glpi.put("Ticket", 4, priority=2)
        assert _orchestrator(config).push_changes(control, ["name"]) is True
        assert glpi.writes == [("Ticket", "4", {"name": "Renamed locally"})]
        link.refresh_from_db()
        assert link.remote_data["fields"]["name"] == "Renamed locally"
        assert link.remote_data["fields"]["priority"] == 5

        assert _orchestrator(config).handle_webhook_event("update", update) is True
        control.refresh_from_db()
        assert (control.name, control.priority) == ("Renamed locally", 4)
        assert glpi.items[("Ticket", "4")]["name"] == "Renamed locally"


def test_glpi_asset_without_a_mapped_field_is_not_pushed(root_folder):
    from core.models import Asset
    from integrations.models import SyncMapping

    config = _glpi_config(root_folder, models={"asset": {"table_name": "Computer"}})
    asset = Asset.objects.create(name="Asset", folder=root_folder)

    with FakeGLPI() as glpi:
        assert _orchestrator(config).push_changes(asset, []) is False
        assert glpi.writes == []
    assert not SyncMapping.objects.filter(configuration=config).exists()


def test_glpi_asset_picker_lists_the_asset_item_type(admin_client, root_folder):
    config = IntegrationConfiguration.objects.create(
        provider=IntegrationProvider.objects.get(name="glpi"),
        folder=root_folder,
        credentials=GLPI_CREDENTIALS,
        settings={"table_name": "Ticket", "models": {"asset": {"table_name": "Phone"}}},
    )
    answer = MagicMock(status_code=200)
    answer.json.return_value = [{"id": 9, "name": "Desk phone"}]

    with (
        patch("integrations.itsm.glpi.client.check_integration_url"),
        patch("integrations.itsm.glpi.client.GLPIClient._get_token", return_value="t"),
        patch(
            "integrations.itsm.glpi.client.requests.request", return_value=answer
        ) as request,
    ):
        response = admin_client.get(
            f"{CONFIGS_URL}{config.id}/remote-objects/", {"model_key": "asset"}
        )

    assert response.status_code == 200, response.content
    assert response.json() == [
        {"key": "Phone:9", "id": "Phone:9", "summary": "#9 - Desk phone"}
    ]
    assert request.call_args[0][1] == "https://glpi.example.com/api.php/v2/Assets/Phone"


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
    assert save(client_id="other", password=fresh["password"]).status_code == 400
    config.refresh_from_db()
    assert config.credentials == stored

    # On the same connection, either secret can be replaced on its own.
    for key in ("password", "client_secret"):
        assert save(**{key: fresh[key]}).status_code == 200
        config.refresh_from_db()
        assert config.credentials == {**stored, key: fresh[key]}
        config.credentials = dict(stored)
        config.save(update_fields=["credentials"])

    moved = {**elsewhere, **fresh}
    assert save(**moved).status_code == 200
    config.refresh_from_db()
    assert config.credentials == {**stored, **moved}
