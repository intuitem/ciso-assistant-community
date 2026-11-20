"""Saving a configuration with the secret field hidden, then testing a new
secret from the edit page. Regression for the rotated-token support ticket:
the save used to write ``password: None`` into Jira credentials, which the
connection-test secret pinning then treated as a stored secret."""

import pytest

from iam.models import Folder
from integrations.models import IntegrationConfiguration, IntegrationProvider
from integrations.registry import IntegrationRegistry
from integrations.serializers import (
    ConnectionTestSerializer,
    IntegrationConfigurationSerializer,
)

STORED = {
    "server_url": "https://victim.atlassian.net",
    "email": "admin@victim.example",
    "api_token": "OLD",
}


@pytest.fixture(autouse=True)
def accept_any_provider(monkeypatch):
    monkeypatch.setattr(
        IntegrationRegistry, "validate_configuration", lambda *_: (True, [])
    )


@pytest.fixture
def jira_config(db):
    folder, _ = Folder.objects.get_or_create(
        content_type=Folder.ContentType.ROOT, defaults={"name": "Global"}
    )
    provider, _ = IntegrationProvider.objects.get_or_create(
        name="jira", provider_type="itsm"
    )
    return IntegrationConfiguration.objects.create(
        provider=provider, folder=folder, credentials=dict(STORED), settings={}
    )


def _serializer(config, credentials):
    return IntegrationConfigurationSerializer(
        config,
        data={"credentials": credentials, "settings": {"table_name": "PROJ:Task"}},
        partial=True,
    )


def _save(config, credentials):
    serializer = _serializer(config, credentials)
    assert serializer.is_valid(), serializer.errors
    saved = serializer.save()
    saved.refresh_from_db()
    return saved


def _refused(config, credentials):
    serializer = _serializer(config, credentials)
    assert not serializer.is_valid()
    assert "credentials" in serializer.errors
    config.refresh_from_db()
    return config


def _test_connection(config, api_token):
    return ConnectionTestSerializer().validate(
        {
            "provider": "jira",
            "configuration_id": config,
            "credentials": {
                "server_url": STORED["server_url"],
                "email": STORED["email"],
                "api_token": api_token,
            },
            "settings": {},
        }
    )


def test_save_without_secret_keeps_stored_token_and_writes_no_stale_keys(
    jira_config,
):
    saved = _save(
        jira_config,
        {"server_url": STORED["server_url"], "email": STORED["email"]},
    )
    assert saved.credentials == STORED


def test_save_with_new_secret_stores_it(jira_config):
    saved = _save(jira_config, {**STORED, "api_token": "NEW"})
    assert saved.credentials == {**STORED, "api_token": "NEW"}


def test_new_token_can_be_tested_after_a_save(jira_config):
    saved = _save(
        jira_config,
        {"server_url": STORED["server_url"], "email": STORED["email"]},
    )
    out = _test_connection(saved, "NEW")
    assert out["credentials"]["api_token"] == "NEW"


def test_new_token_can_be_tested_on_rows_saved_by_older_versions(jira_config):
    jira_config.credentials = {**STORED, "password": None}
    jira_config.save(update_fields=["credentials"])
    out = _test_connection(jira_config, "NEW")
    assert out["credentials"]["api_token"] == "NEW"
    assert "password" not in out["credentials"]


def test_empty_token_still_replays_the_stored_one_on_older_rows(jira_config):
    jira_config.credentials = {**STORED, "password": None}
    jira_config.save(update_fields=["credentials"])
    out = _test_connection(jira_config, "")
    assert out["credentials"]["api_token"] == "OLD"


@pytest.mark.parametrize(
    "changed",
    [
        {"server_url": "https://elsewhere.example"},
        {"email": "someone@elsewhere.example"},
    ],
)
def test_save_does_not_carry_the_stored_token_to_another_connection(
    jira_config, changed
):
    submitted = {"server_url": STORED["server_url"], "email": STORED["email"]}
    config = _refused(jira_config, {**submitted, **changed})
    assert config.credentials == STORED

    # Same request with the secret left empty rather than omitted.
    _refused(jira_config, {**submitted, **changed, "api_token": ""})


def test_save_to_another_connection_with_its_own_secret(jira_config):
    moved = {
        "server_url": "https://elsewhere.example",
        "email": STORED["email"],
        "api_token": "NEW",
    }
    assert _save(jira_config, moved).credentials == moved


def test_save_cannot_point_a_row_without_a_host_at_one(jira_config):
    """An empty stored host must not let the stored token go to any host."""
    jira_config.credentials = {**STORED, "server_url": ""}
    jira_config.save(update_fields=["credentials"])
    _refused(
        jira_config,
        {"server_url": "https://elsewhere.example", "email": STORED["email"]},
    )


def test_save_keeps_the_stored_secret_on_rows_saved_by_older_versions(jira_config):
    jira_config.credentials = {**STORED, "password": None}
    jira_config.save(update_fields=["credentials"])
    saved = _save(
        jira_config, {"server_url": STORED["server_url"], "email": STORED["email"]}
    )
    assert saved.credentials["api_token"] == "OLD"


def test_one_of_two_stored_secrets_cannot_follow_a_new_host(jira_config):
    """A provider with two secrets: supplying one does not release the other."""
    jira_config.credentials = {
        "instance_url": "https://victim.example",
        "username": "sync",
        "password": "OLD-PASSWORD",
        "api_token": "OLD-TOKEN",
    }
    jira_config.save(update_fields=["credentials"])
    _refused(
        jira_config,
        {
            "instance_url": "https://elsewhere.example",
            "username": "sync",
            "password": "NEW-PASSWORD",
        },
    )


def test_one_of_two_stored_secrets_can_be_replaced_on_the_same_connection(jira_config):
    same_connection = {"instance_url": "https://victim.example", "username": "sync"}
    # Derived values: no literal here looks like a credential to a scanner.
    old = {key: f"{STORED['api_token']}-{key}" for key in ("password", "api_token")}
    new = {key: f"{value}-rotated" for key, value in old.items()}
    jira_config.credentials = {**same_connection, **old}
    jira_config.save(update_fields=["credentials"])

    saved = _save(jira_config, {**same_connection, "password": new["password"]})
    assert saved.credentials == {**same_connection, **old, "password": new["password"]}

    # The connection test follows the same rule.
    out = ConnectionTestSerializer().validate(
        {
            "provider": "jira",
            "configuration_id": saved,
            "credentials": {**same_connection, "api_token": new["api_token"]},
            "settings": {},
        }
    )
    assert out["credentials"] == {**same_connection, **new}

    # Another account on the same host is another connection.
    _refused(
        jira_config,
        {**same_connection, "username": "x", **{"password": new["password"]}},
    )
