"""Tests for the SSO-disable guard in SSOSettingsWriteSerializer.update().

The stored value dict is replaced wholesale on update, so an omitted flag must
fall back to the stored state: before the fix, a payload that simply left out
`is_enabled` silently disabled SSO (stranding SSO-only users) while skirting
the guard, which only reacted to an explicit False.
"""

import pytest
from rest_framework import serializers as drf_serializers

from global_settings.models import GlobalSettings
from iam.models import User
from iam.sso.serializers import SSOSettingsWriteSerializer


def _make_sso_settings(is_enabled=True, force_sso=False):
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": is_enabled,
                "force_sso": force_sso,
                "provider": "openid_connect",
                "provider_id": "test-oidc",
                "name": "Test OIDC",
                "client_id": "client-id",
                "settings": {},
            }
        },
    )


def _stored_value():
    return GlobalSettings.objects.get(name=GlobalSettings.Names.SSO).value


def _make_scim_user(email):
    user = User.objects.create_user(email)
    user.is_scim_managed = True
    user.save(update_fields=["is_scim_managed"])
    return user


def _update(payload):
    """Call update() with validated_data shaped the way to_internal_value builds
    it: dotted sources produce nested mappings only for the fields actually
    received, so a payload with no `settings.*` field carries no `settings` key
    at all. Passing the payload through untouched keeps that true — update() is
    responsible for normalizing it."""
    return SSOSettingsWriteSerializer().update(None, payload)


@pytest.mark.django_db
class TestSsoDisableGuard:
    def test_omitting_is_enabled_keeps_sso_enabled(self):
        """The bypass: omission must preserve the stored state, not silently
        disable SSO behind the guard's back."""
        _make_sso_settings(is_enabled=True)
        _make_scim_user("scim.stranded@tests.com")

        _update({"provider": "openid_connect"})

        assert _stored_value()["is_enabled"] is True

    def test_omitting_force_sso_keeps_stored_value(self):
        _make_sso_settings(is_enabled=True, force_sso=True)

        _update({"provider": "openid_connect"})

        assert _stored_value()["force_sso"] is True

    def test_disabling_with_stranded_scim_users_is_blocked(self):
        _make_sso_settings(is_enabled=True)
        _make_scim_user("scim.stranded2@tests.com")

        with pytest.raises(drf_serializers.ValidationError) as excinfo:
            _update({"is_enabled": False, "provider": "openid_connect"})

        assert "errorSsoRequiredForManagedUsers" in str(excinfo.value)
        assert _stored_value()["is_enabled"] is True

    def test_disabling_without_sso_only_users_succeeds(self):
        _make_sso_settings(is_enabled=True)

        _update({"is_enabled": False, "provider": "openid_connect"})

        assert _stored_value()["is_enabled"] is False

    def test_resaving_an_already_disabled_config_is_allowed(self):
        """Transition semantics: the guard protects the enabled -> disabled
        step only, so configuring SSO before enabling it stays possible even
        while SCIM users exist."""
        _make_sso_settings(is_enabled=False)
        _make_scim_user("scim.preexisting@tests.com")

        _update({"is_enabled": False, "provider": "openid_connect"})

        assert _stored_value()["is_enabled"] is False


@pytest.mark.django_db
class TestNestedSettingsNormalization:
    """update() indexes into settings["advanced"], which to_internal_value only
    builds when the payload actually carried a `settings.advanced.*` field."""

    def test_payload_without_any_settings_field_is_accepted(self):
        """A partial payload: DRF skips defaults, so no dotted source fires and
        `settings` is absent entirely."""
        _make_sso_settings(is_enabled=True)

        _update({"provider": "openid_connect"})

        assert _stored_value()["settings"]["advanced"]["private_key"] == ""

    def test_oidc_payload_without_advanced_fields_is_accepted(self):
        """A full OIDC save: `oauth_pkce_enabled` has a default, so `settings`
        exists — but `advanced` is SAML-only and stays absent."""
        _make_sso_settings(is_enabled=True)

        _update(
            {
                "provider": "openid_connect",
                "settings": {"oauth_pkce_enabled": False, "server_url": "https://idp"},
            }
        )

        assert _stored_value()["settings"]["advanced"]["private_key"] == ""
        assert _stored_value()["settings"]["server_url"] == "https://idp"

    def test_stored_private_key_survives_a_payload_that_omits_it(self):
        """The fallback the indexing exists for: an omitted key must not be
        wiped by a save that never mentions it."""
        _make_sso_settings(is_enabled=True)
        stored = GlobalSettings.objects.get(name=GlobalSettings.Names.SSO)
        stored.value["settings"] = {"advanced": {"private_key": "KEEP-ME"}}
        stored.save()

        _update({"provider": "saml"})

        assert _stored_value()["settings"]["advanced"]["private_key"] == "KEEP-ME"
