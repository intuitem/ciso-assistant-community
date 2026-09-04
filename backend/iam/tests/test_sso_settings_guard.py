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
    """Call update() the way save() does; `settings.advanced` must exist the
    way to_internal_value's dotted sources would have built it."""
    payload.setdefault("settings", {}).setdefault("advanced", {})
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
