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
    """A payload shaped the way to_internal_value builds one for a form save."""
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
class TestPartialPayloadPreservesStoredSections:
    """update() replaces the stored value wholesale, and to_internal_value builds
    a nested mapping only for the dotted sources a payload actually carries. So
    every real save is "partial" in some section: an OIDC form save renders no
    SAML accordion and therefore sends no `settings.advanced.*` at all. The
    sections the payload omits are merged back from the stored value instead of
    being dropped.
    """

    def test_oidc_shaped_save_is_accepted(self):
        """The shape a real OIDC form save produces — no `settings.advanced.*`
        field anywhere. It must save, not 400."""
        _make_saml_settings()

        _update(
            {
                "provider": "openid_connect",
                "client_id": "oidc-client",
                "settings": {
                    "server_url": "https://idp",
                    "oauth_pkce_enabled": True,
                },
            }
        )

        stored = _stored_value()
        assert stored["provider"] == "openid_connect"
        assert stored["settings"]["server_url"] == "https://idp"

    def test_omitted_sections_keep_their_stored_contents(self):
        """The point of merging: a payload that touches one section must not
        wipe the others."""
        _make_saml_settings()

        _update(
            {
                "provider": "saml",
                "settings": {"idp": {"entity_id": "NEW-IDP"}},
            }
        )

        stored = _stored_value()
        assert stored["settings"]["idp"]["entity_id"] == "NEW-IDP"
        assert stored["settings"]["sp"]["entity_id"] == "STORED-SP"
        assert stored["settings"]["advanced"]["signature_algorithm"] == "rsa-sha256"
        assert stored["settings"]["advanced"]["private_key"] == "STORED-PRIVATE-KEY"

    def test_omitted_leaves_within_a_touched_section_are_kept(self):
        """Merging descends one level, so sending one advanced flag does not
        drop the rest of `advanced` — the SP private key above all."""
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

    def test_narrow_patch_keeps_provider_and_client_id(self):
        """A payload carrying no `settings.*` field at all (a narrow API PATCH):
        the top-level fields it omits fall back to the stored value rather than
        resetting to a default, exactly like is_enabled."""
        _make_saml_settings()

        _update({"is_enabled": False})

        stored = _stored_value()
        assert stored["is_enabled"] is False
        assert stored["provider"] == "saml"
        assert stored["provider_id"] == "saml"
        assert stored["client_id"] == "stored-client"
        assert stored["settings"]["idp"]["entity_id"] == "STORED-IDP"
        assert stored["settings"]["sp"]["entity_id"] == "STORED-SP"
        assert stored["settings"]["advanced"]["private_key"] == "STORED-PRIVATE-KEY"

    def test_first_save_on_an_empty_settings_dict_works(self):
        """A fresh deployment has no nested sections stored at all; the
        private-key restore must not trip over the missing `advanced`."""
        GlobalSettings.objects.update_or_create(
            name=GlobalSettings.Names.SSO,
            defaults={"value": {"is_enabled": False, "settings": {}}},
        )

        _update({"provider": "openid_connect", "settings": {"server_url": "https://x"}})

        stored = _stored_value()
        assert stored["settings"]["server_url"] == "https://x"
        assert stored["settings"]["advanced"]["private_key"] == ""
