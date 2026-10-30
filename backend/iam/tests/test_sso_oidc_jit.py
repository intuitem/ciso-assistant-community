from unittest.mock import MagicMock

import pytest
from django.test import RequestFactory

from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.adapter import SocialAccountAdapter
from iam.models import IdPGroup, User, UserGroup


class FakeAccount:
    def __init__(self, extra_data, provider="openid_connect"):
        self.extra_data = extra_data
        self.provider = provider


class FakeUser:
    def __init__(self, first_name="", last_name=""):
        self.first_name = first_name
        self.last_name = last_name


class FakeSocialLogin:
    def __init__(
        self, extra_data, first_name="", last_name="", provider="openid_connect"
    ):
        self.account = FakeAccount(extra_data, provider)
        self.user = FakeUser(first_name, last_name)
        self.connect = MagicMock()


def _set_feature_flag(name, value):
    settings, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS,
        defaults={"value": {}},
    )
    settings.value = {**(settings.value or {}), name: value}
    settings.save(update_fields=["value"])
    clear_feature_flags_cache()


def _make_sso_settings(
    jit_provisioning_enabled=False, default_user_groups=None, attribute_mapping=None
):
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": True,
                "provider": "openid_connect",
                "provider_id": "test-oidc",
                "name": "Test OIDC",
                "client_id": "client-id",
                "jit_provisioning_enabled": jit_provisioning_enabled,
                "default_user_groups": default_user_groups or [],
                "settings": {"attribute_mapping": attribute_mapping or {}},
            }
        },
    )


@pytest.mark.django_db
class TestOIDCPreSSOMainBehavior:
    def test_existing_user_is_matched_and_connected(self):
        user = User.objects.create_user(email="alice@example.com", password="pw")
        sociallogin = FakeSocialLogin(extra_data={"email": "alice@example.com"})
        request = RequestFactory().get("/")

        response = SocialAccountAdapter().pre_social_login(request, sociallogin)

        assert response is None
        assert sociallogin.user == user
        sociallogin.connect.assert_called_once_with(request, user)

    def test_unknown_email_without_sso_settings_returns_401(self):
        sociallogin = FakeSocialLogin(extra_data={"email": "ghost@example.com"})
        request = RequestFactory().get("/")

        response = SocialAccountAdapter().pre_social_login(request, sociallogin)

        assert response is not None
        assert response.status_code == 401
        assert not User.objects.filter(email="ghost@example.com").exists()

    def test_unknown_email_with_jit_flag_off_returns_401(self):
        _make_sso_settings(jit_provisioning_enabled=True)
        _set_feature_flag("jit_provisioning", False)

        sociallogin = FakeSocialLogin(extra_data={"email": "ghost@example.com"})
        request = RequestFactory().get("/")

        response = SocialAccountAdapter().pre_social_login(request, sociallogin)

        assert response is not None
        assert response.status_code == 401
        assert not User.objects.filter(email="ghost@example.com").exists()

    def test_unknown_email_with_jit_setting_disabled_returns_401(self):
        _make_sso_settings(jit_provisioning_enabled=False)
        _set_feature_flag("jit_provisioning", True)

        sociallogin = FakeSocialLogin(extra_data={"email": "ghost@example.com"})
        request = RequestFactory().get("/")

        response = SocialAccountAdapter().pre_social_login(request, sociallogin)

        assert response is not None
        assert response.status_code == 401
        assert not User.objects.filter(email="ghost@example.com").exists()

    def test_no_email_in_extra_data_returns_401(self):
        sociallogin = FakeSocialLogin(extra_data={"sub": "1234"})
        request = RequestFactory().get("/")

        response = SocialAccountAdapter().pre_social_login(request, sociallogin)

        assert response is not None
        assert response.status_code == 401

    def test_existing_user_not_group_synced_when_jit_flag_off(self):
        user = User.objects.create_user(email="bob@example.com", password="pw")
        sociallogin = FakeSocialLogin(
            extra_data={"email": "bob@example.com", "groups": ["Engineering"]}
        )
        request = RequestFactory().get("/")

        SocialAccountAdapter().pre_social_login(request, sociallogin)

        user.refresh_from_db()
        assert list(user.idp_groups.all()) == []
        assert not IdPGroup.objects.filter(name="Engineering").exists()


@pytest.mark.django_db
class TestOIDCPreSSOJitProvisioning:
    def test_jit_creates_user_with_expected_fields(self):
        group = UserGroup.objects.create(name="Analysts")
        _make_sso_settings(
            jit_provisioning_enabled=True, default_user_groups=[str(group.id)]
        )
        _set_feature_flag("jit_provisioning", True)

        sociallogin = FakeSocialLogin(
            extra_data={"email": "new.user@example.com"},
            first_name="New",
            last_name="User",
        )
        request = RequestFactory().get("/")

        response = SocialAccountAdapter().pre_social_login(request, sociallogin)

        assert response is None
        user = User.objects.get(email="new.user@example.com")
        assert user.is_jit_provisioned is True
        assert user.first_name == "New"
        assert user.last_name == "User"
        assert list(user.user_groups.all()) == [group]
        assert sociallogin.user == user
        sociallogin.connect.assert_called_once_with(request, user)

    def test_jit_creation_syncs_idp_groups_with_sso_source(self):
        _make_sso_settings(jit_provisioning_enabled=True)
        _set_feature_flag("jit_provisioning", True)

        sociallogin = FakeSocialLogin(
            extra_data={"email": "new.user@example.com", "groups": ["Engineering"]},
        )
        request = RequestFactory().get("/")

        SocialAccountAdapter().pre_social_login(request, sociallogin)

        user = User.objects.get(email="new.user@example.com")
        idp_group = IdPGroup.objects.get(name="Engineering")
        assert idp_group.source == IdPGroup.Source.SSO
        assert list(user.idp_groups.all()) == [idp_group]

    def test_group_sync_also_runs_for_existing_user_when_jit_active(self):
        user = User.objects.create_user(email="carol@example.com", password="pw")
        _make_sso_settings(jit_provisioning_enabled=True)
        _set_feature_flag("jit_provisioning", True)

        sociallogin = FakeSocialLogin(
            extra_data={"email": "carol@example.com", "groups": ["Sales"]}
        )
        request = RequestFactory().get("/")

        SocialAccountAdapter().pre_social_login(request, sociallogin)

        user.refresh_from_db()
        idp_group = IdPGroup.objects.get(name="Sales")
        assert list(user.idp_groups.all()) == [idp_group]

    def test_empty_group_claim_clears_previous_membership(self):
        user = User.objects.create_user(email="dora@example.com", password="pw")
        stale_group = IdPGroup.objects.create(
            name="Old Group", source=IdPGroup.Source.SSO
        )
        user.idp_groups.add(stale_group)
        _make_sso_settings(jit_provisioning_enabled=True)
        _set_feature_flag("jit_provisioning", True)

        sociallogin = FakeSocialLogin(
            extra_data={"email": "dora@example.com", "groups": []}
        )
        request = RequestFactory().get("/")

        SocialAccountAdapter().pre_social_login(request, sociallogin)

        user.refresh_from_db()
        assert list(user.idp_groups.all()) == []

    def test_scim_managed_user_group_membership_is_not_touched(self):
        user = User.objects.create_user(email="eve@example.com", password="pw")
        user.is_scim_managed = True
        user.save(update_fields=["is_scim_managed"])
        scim_group = IdPGroup.objects.create(
            name="SCIM Group", source=IdPGroup.Source.SCIM
        )
        user.idp_groups.add(scim_group)
        _make_sso_settings(jit_provisioning_enabled=True)
        _set_feature_flag("jit_provisioning", True)

        sociallogin = FakeSocialLogin(
            extra_data={"email": "eve@example.com", "groups": ["Something Else"]}
        )
        request = RequestFactory().get("/")

        SocialAccountAdapter().pre_social_login(request, sociallogin)

        user.refresh_from_db()
        assert list(user.idp_groups.all()) == [scim_group]
        assert not IdPGroup.objects.filter(name="Something Else").exists()
