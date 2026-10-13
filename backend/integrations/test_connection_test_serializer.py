import pytest
from rest_framework import serializers

from integrations.registry import IntegrationRegistry
from integrations.serializers import ConnectionTestSerializer

STORED = {
    "server_url": "https://victim.atlassian.net",
    "email": "admin@victim.example",
    "api_token": "s3cret",
}


class StubProvider:
    name = "jira"


class StubConfig:
    credentials = STORED
    provider = StubProvider()


@pytest.fixture(autouse=True)
def accept_any_provider(monkeypatch):
    monkeypatch.setattr(
        IntegrationRegistry, "validate_configuration", lambda *_: (True, [])
    )


def _validate(
    credentials, config: StubConfig | None = StubConfig(), provider: str = "jira"
):
    return ConnectionTestSerializer().validate(
        {
            "provider": provider,
            "configuration_id": config,
            "credentials": credentials,
            "settings": {},
        }
    )


def test_backfills_when_connection_is_unchanged():
    data = _validate(
        {
            "server_url": STORED["server_url"],
            "email": STORED["email"],
            "api_token": "",
        }
    )
    assert data["credentials"]["api_token"] == "s3cret"


def test_rejects_backfill_to_a_different_host():
    with pytest.raises(serializers.ValidationError):
        _validate(
            {
                "server_url": "https://attacker.example",
                "email": STORED["email"],
                "api_token": "",
            }
        )


def test_rejects_backfill_to_a_different_account():
    with pytest.raises(serializers.ValidationError):
        _validate(
            {
                "server_url": STORED["server_url"],
                "email": "attacker@evil.example",
                "api_token": "",
            }
        )


def test_supplied_secret_is_never_replaced_by_the_stored_one():
    data = _validate(
        {
            "server_url": "https://attacker.example",
            "email": "attacker@evil.example",
            "api_token": "attacker-token",
        }
    )
    assert data["credentials"]["api_token"] == "attacker-token"


def test_does_not_mutate_the_incoming_credentials():
    credentials = {
        "server_url": STORED["server_url"],
        "email": STORED["email"],
        "api_token": "",
    }
    _validate(credentials)
    assert credentials["api_token"] == ""


def test_rejects_backfill_through_a_different_provider():
    with pytest.raises(serializers.ValidationError):
        _validate(
            {"instance_url": "https://attacker.example", "username": "x"},
            provider="servicenow",
        )


def test_no_config_leaves_credentials_untouched():
    data = _validate({"server_url": "https://anywhere.example"}, config=None)
    assert data["credentials"] == {"server_url": "https://anywhere.example"}
