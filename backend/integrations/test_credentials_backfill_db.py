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


def _save(config, credentials):
    serializer = IntegrationConfigurationSerializer(
        config,
        data={"credentials": credentials, "settings": {"table_name": "PROJ:Task"}},
        partial=True,
    )
    assert serializer.is_valid(), serializer.errors
    saved = serializer.save()
    saved.refresh_from_db()
    return saved


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
