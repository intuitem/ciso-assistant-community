from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.http import HttpRequest
from rest_framework import serializers as drf_serializers

from global_settings.models import GlobalSettings
from iam.sso.oidc.views import _get_oidc_scopes
from iam.sso.serializers import SSOSettingsWriteSerializer


def _provider(additional_scopes=""):
    provider = Mock()
    provider.get_scope_from_request.return_value = ["openid", "profile", "email"]
    provider.app = SimpleNamespace(settings={"additional_scopes": additional_scopes})
    return provider


def test_additional_scopes_are_appended_to_default_oidc_scopes():
    provider = _provider("custom:read, custom:write")

    assert _get_oidc_scopes(provider, HttpRequest()) == [
        "openid",
        "profile",
        "email",
        "custom:read",
        "custom:write",
    ]


def test_additional_scopes_are_not_duplicated():
    provider = _provider("email, custom:read, custom:read")

    assert _get_oidc_scopes(provider, HttpRequest()) == [
        "openid",
        "profile",
        "email",
        "custom:read",
    ]


def test_additional_scopes_are_deserialized_into_settings():
    serializer = SSOSettingsWriteSerializer(
        data={"additional_scopes": "custom:read, custom:write"}
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["settings"]["additional_scopes"] == (
        "custom:read, custom:write"
    )


@pytest.mark.django_db
def test_additional_scopes_are_saved_in_sso_settings():
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": False,
                "provider": "openid_connect",
                "client_id": "client-id",
                "settings": {},
            }
        },
    )
    serializer = SSOSettingsWriteSerializer(
        data={"additional_scopes": "custom:read, custom:write"}
    )

    assert serializer.is_valid(), serializer.errors
    serializer.update(None, serializer.validated_data)

    stored = GlobalSettings.objects.get(name=GlobalSettings.Names.SSO).value
    assert stored["settings"]["additional_scopes"] == "custom:read, custom:write"


@pytest.mark.parametrize(
    "scopes", ["two scopes", "scope,", ",scope", 'bad"scope', r"bad\\scope"]
)
def test_additional_scopes_reject_invalid_oauth_scope_tokens(scopes):
    serializer = SSOSettingsWriteSerializer(data={"additional_scopes": scopes})

    with pytest.raises(drf_serializers.ValidationError):
        serializer.is_valid(raise_exception=True)
