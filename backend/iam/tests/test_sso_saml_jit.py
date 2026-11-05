from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpRequest
from django.test import Client
from django.urls import reverse

from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import IdPGroup, User, UserGroup

GIVENNAME_URI = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
SURNAME_URI = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"
EMAIL_URI = "test-email-uri"
GROUPS_URI = "groups"


def _set_feature_flag(name, value):
    settings, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS,
        defaults={"value": {}},
    )
    settings.value = {**(settings.value or {}), name: value}
    settings.save(update_fields=["value"])
    clear_feature_flags_cache()


def _make_sso_settings(jit_provisioning_enabled=False, default_user_groups=None):
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": True,
                "provider": "saml",
                "provider_id": "test-saml",
                "name": "Test SAML",
                "client_id": "client-id",
                "jit_provisioning_enabled": jit_provisioning_enabled,
                "default_user_groups": default_user_groups or [],
                "settings": {
                    "attribute_mapping": {"email": [EMAIL_URI], "groups": [GROUPS_URI]},
                    "advanced": {"reject_idp_initiated_sso": False},
                },
            }
        },
    )


def _make_mock_auth(nameid, attributes=None):
    attrs = attributes or {}
    auth = MagicMock()
    auth.process_response.return_value = None
    auth.get_errors.return_value = []
    auth.is_authenticated.return_value = True
    auth.get_last_response_in_response_to.return_value = None
    auth.get_nameid.return_value = nameid
    auth.get_attribute.side_effect = lambda uri: attrs.get(uri, [])
    return auth


def _make_mock_provider(app):
    provider = MagicMock()
    provider.app = app
    login = MagicMock()
    login.state = {}
    provider.sociallogin_from_response.return_value = login
    return provider


def _call_finish_acs(auth, sso_settings=None):
    from iam.sso.models import SSOSettings

    app = sso_settings or SSOSettings.objects.get()
    provider = _make_mock_provider(app)

    session_instance = MagicMock()
    session_instance.store = {"request": "dummy"}

    with (
        patch("iam.sso.saml.views.FinishACSView.get_provider", return_value=provider),
        patch("iam.sso.saml.views.build_auth", return_value=auth),
        patch("iam.sso.saml.views.LoginSession", return_value=session_instance),
        patch(
            "iam.sso.saml.views.httpkit.deserialize_request",
            return_value=HttpRequest(),
        ),
        patch("iam.sso.saml.views.pre_social_login"),
        patch("iam.sso.saml.views.record_authentication"),
        patch("iam.sso.saml.views.stash_saml_slo_state"),
    ):
        client = Client()
        url = reverse("saml_finish_acs", kwargs={"organization_slug": "default"})
        return client.get(url)


@pytest.mark.django_db
class TestSAMLMainBehavior:
    def test_existing_user_is_matched_by_nameid(self):
        User.objects.create_user(email="alice@example.com", password="pw")
        _make_sso_settings()
        auth = _make_mock_auth(nameid="alice@example.com")

        response = _call_finish_acs(auth)

        assert response.status_code == 302
        assert "error" not in response.url

    def test_existing_user_name_is_synced_from_idp_claims_every_login(self):
        user = User.objects.create_user(
            email="alice@example.com",
            password="pw",
            first_name="Stale",
            last_name="Name",
        )
        _make_sso_settings()
        auth = _make_mock_auth(
            nameid="alice@example.com",
            attributes={GIVENNAME_URI: ["Alice"], SURNAME_URI: ["Wonderland"]},
        )

        _call_finish_acs(auth)

        user.refresh_from_db()
        assert user.first_name == "Alice"
        assert user.last_name == "Wonderland"

    def test_unknown_user_without_jit_is_rejected(self):
        _make_sso_settings(jit_provisioning_enabled=False)
        auth = _make_mock_auth(
            nameid="ghost@example.com",
            attributes={EMAIL_URI: ["ghost@example.com"]},
        )

        response = _call_finish_acs(auth)

        assert response.status_code == 302
        assert "error" in response.url
        assert not User.objects.filter(email="ghost@example.com").exists()

    def test_name_sync_does_not_overwrite_when_idp_sends_no_name(self):
        user = User.objects.create_user(
            email="alice@example.com",
            password="pw",
            first_name="Keep",
            last_name="Me",
        )
        _make_sso_settings()
        auth = _make_mock_auth(nameid="alice@example.com", attributes={})

        _call_finish_acs(auth)

        user.refresh_from_db()
        assert user.first_name == "Keep"
        assert user.last_name == "Me"


@pytest.mark.django_db
class TestSAMLJitProvisioning:
    def test_jit_creates_user_via_email_fallback(self):
        group = UserGroup.objects.create(name="Analysts")
        _make_sso_settings(
            jit_provisioning_enabled=True, default_user_groups=[str(group.id)]
        )
        _set_feature_flag("jit_provisioning", True)
        auth = _make_mock_auth(
            nameid="unmatched-nameid",
            attributes={
                EMAIL_URI: ["new.saml.user@example.com"],
                GIVENNAME_URI: ["New"],
                SURNAME_URI: ["User"],
            },
        )

        response = _call_finish_acs(auth)

        assert response.status_code == 302
        assert "error" not in response.url
        user = User.objects.get(email="new.saml.user@example.com")
        assert user.is_jit_provisioned is True
        assert user.first_name == "New"
        assert user.last_name == "User"
        assert list(user.user_groups.all()) == [group]

    def test_jit_creation_syncs_idp_groups_with_sso_source(self):
        _make_sso_settings(jit_provisioning_enabled=True)
        _set_feature_flag("jit_provisioning", True)
        auth = _make_mock_auth(
            nameid="unmatched-nameid",
            attributes={
                EMAIL_URI: ["new.saml.user@example.com"],
                GROUPS_URI: ["Engineering"],
            },
        )

        _call_finish_acs(auth)

        user = User.objects.get(email="new.saml.user@example.com")
        idp_group = IdPGroup.objects.get(name="Engineering")
        assert idp_group.source == IdPGroup.Source.SSO
        assert list(user.idp_groups.all()) == [idp_group]

    def test_jit_flag_off_leaves_unknown_user_rejected_even_if_per_provider_enabled(
        self,
    ):
        _make_sso_settings(jit_provisioning_enabled=True)
        _set_feature_flag("jit_provisioning", False)
        auth = _make_mock_auth(
            nameid="unmatched-nameid",
            attributes={EMAIL_URI: ["new.saml.user@example.com"]},
        )

        response = _call_finish_acs(auth)

        assert response.status_code == 302
        assert "error" in response.url
        assert not User.objects.filter(email="new.saml.user@example.com").exists()
