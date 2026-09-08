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
    at all. Passed through untouched so those shapes stay authentic."""
    return SSOSettingsWriteSerializer().update(None, payload)


def _complete(**overrides):
    """A payload shaped the way to_internal_value builds one for a form that did
    submit SAML advanced fields, so `settings.advanced` exists. update() requires
    that mapping and rejects anything without it, so the guard tests below have
    to clear that bar before they can exercise what they are actually about."""
    payload = {
        "provider": "openid_connect",
        "settings": {"advanced": {"want_assertion_signed": True}},
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestSsoDisableGuard:
    def test_omitting_is_enabled_keeps_sso_enabled(self):
        """The bypass: omission must preserve the stored state, not silently
        disable SSO behind the guard's back."""
        _make_sso_settings(is_enabled=True)
        _make_scim_user("scim.stranded@tests.com")

        _update(_complete())

        assert _stored_value()["is_enabled"] is True

    def test_omitting_force_sso_keeps_stored_value(self):
        _make_sso_settings(is_enabled=True, force_sso=True)

        _update(_complete())

        assert _stored_value()["force_sso"] is True

    def test_disabling_with_stranded_scim_users_is_blocked(self):
        _make_sso_settings(is_enabled=True)
        _make_scim_user("scim.stranded2@tests.com")

        with pytest.raises(drf_serializers.ValidationError) as excinfo:
            _update(_complete(is_enabled=False))

        assert "errorSsoRequiredForManagedUsers" in str(excinfo.value)
        assert _stored_value()["is_enabled"] is True

    def test_disabling_without_sso_only_users_succeeds(self):
        _make_sso_settings(is_enabled=True)

        _update(_complete(is_enabled=False))

        assert _stored_value()["is_enabled"] is False

    def test_resaving_an_already_disabled_config_is_allowed(self):
        """Transition semantics: the guard protects the enabled -> disabled
        step only, so configuring SSO before enabling it stays possible even
        while SCIM users exist."""
        _make_sso_settings(is_enabled=False)
        _make_scim_user("scim.preexisting@tests.com")

        _update(_complete(is_enabled=False))

        assert _stored_value()["is_enabled"] is False


def _make_saml_settings():
    """A fully configured SAML deployment, so a rejected save has something
    substantial to lose."""
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": True,
                "force_sso": False,
                "provider": "saml",
                "provider_id": "saml",
                "client_id": "stored-client",
                "settings": {
                    "idp": {"entity_id": "STORED-IDP"},
                    "sp": {"entity_id": "STORED-SP"},
                    "advanced": {
                        "signature_algorithm": "rsa-sha256",
                        "private_key": "STORED-PRIVATE-KEY",
                    },
                },
            }
        },
    )


@pytest.mark.django_db
class TestIncompletePayloadIsRejected:
    """update() replaces the stored value wholesale, so it requires the nested
    `settings.advanced` mapping that to_internal_value only builds for payloads
    actually carrying a `settings.advanced.*` field. Defaulting that mapping
    instead of refusing would turn a loud failure into a silent one: the save
    proceeds and drops every stored setting the payload left out.
    """

    def test_payload_without_any_settings_field_is_rejected(self):
        """A narrow API PATCH (`{"is_enabled": false}`): DRF skips field
        defaults when partial, so no dotted source fires and `settings` is
        absent entirely."""
        _make_saml_settings()

        with pytest.raises(drf_serializers.ValidationError) as excinfo:
            _update({"is_enabled": False})

        assert "errorSsoSettingsPayloadIncomplete" in str(excinfo.value)

    def test_payload_without_advanced_mapping_is_rejected(self):
        """`settings` present (a dotted OIDC source fired) but `advanced` still
        absent — the case that used to raise KeyError."""
        _make_saml_settings()

        with pytest.raises(drf_serializers.ValidationError) as excinfo:
            _update(
                {
                    "provider": "openid_connect",
                    "settings": {
                        "oauth_pkce_enabled": False,
                        "server_url": "https://idp",
                    },
                }
            )

        assert "errorSsoSettingsPayloadIncomplete" in str(excinfo.value)

    def test_rejected_payload_leaves_the_stored_config_untouched(self):
        """The point of refusing: nothing is written, so a partial call cannot
        strand SSO-only users behind a wiped-but-still-enabled configuration."""
        _make_saml_settings()

        with pytest.raises(drf_serializers.ValidationError):
            _update({"is_enabled": False})

        stored = _stored_value()
        assert stored["provider"] == "saml"
        assert stored["client_id"] == "stored-client"
        assert stored["settings"]["idp"]["entity_id"] == "STORED-IDP"
        assert stored["settings"]["sp"]["entity_id"] == "STORED-SP"
        assert stored["settings"]["advanced"]["signature_algorithm"] == "rsa-sha256"

    def test_payload_carrying_the_advanced_mapping_is_accepted(self):
        """The complete shape a real form save produces still goes through, and
        the stored private key is still restored when omitted."""
        _make_saml_settings()

        _update(
            {
                "provider": "saml",
                "settings": {"advanced": {"signature_algorithm": "rsa-sha512"}},
            }
        )

        stored = _stored_value()
        assert stored["settings"]["advanced"]["signature_algorithm"] == "rsa-sha512"
        assert stored["settings"]["advanced"]["private_key"] == "STORED-PRIVATE-KEY"
