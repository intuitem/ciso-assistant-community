from unittest.mock import MagicMock

import pytest
from django.core.exceptions import ValidationError
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
    jit_provisioning_enabled=False,
    default_user_groups=None,
    attribute_mapping=None,
    provider="openid_connect",
    trust_unverified_email=False,
):
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": True,
                "provider": provider,
                "provider_id": "test-oidc",
                "name": "Test OIDC",
                "client_id": "client-id",
                "jit_provisioning_enabled": jit_provisioning_enabled,
                "default_user_groups": default_user_groups or [],
                "settings": {
                    "attribute_mapping": attribute_mapping or {},
                    "trust_email_without_verified_claim": trust_unverified_email,
                },
            }
        },
    )


@pytest.mark.django_db
class TestOIDCPreSSOMainBehavior:
    def test_existing_user_is_matched_and_connected(self):
        user = User.objects.create_user(email="alice@example.com", password="pw")
        sociallogin = FakeSocialLogin(
            extra_data={"email": "alice@example.com", "email_verified": True}
        )
        request = RequestFactory().get("/")

        response = SocialAccountAdapter().pre_social_login(request, sociallogin)

        assert response is None
        assert sociallogin.user == user
        sociallogin.connect.assert_called_once_with(request, user)

    def test_unknown_email_without_sso_settings_returns_401(self):
        sociallogin = FakeSocialLogin(
            extra_data={"email": "ghost@example.com", "email_verified": True}
        )
        request = RequestFactory().get("/")

        response = SocialAccountAdapter().pre_social_login(request, sociallogin)

        assert response is not None
        assert response.status_code == 401
        assert not User.objects.filter(email="ghost@example.com").exists()

    def test_unknown_email_with_jit_flag_off_returns_401(self):
        _make_sso_settings(jit_provisioning_enabled=True)
        _set_feature_flag("jit_provisioning", False)

        sociallogin = FakeSocialLogin(
            extra_data={"email": "ghost@example.com", "email_verified": True}
        )
        request = RequestFactory().get("/")

        response = SocialAccountAdapter().pre_social_login(request, sociallogin)

        assert response is not None
        assert response.status_code == 401
        assert not User.objects.filter(email="ghost@example.com").exists()

    def test_unknown_email_with_jit_setting_disabled_returns_401(self):
        _make_sso_settings(jit_provisioning_enabled=False)
        _set_feature_flag("jit_provisioning", True)

        sociallogin = FakeSocialLogin(
            extra_data={"email": "ghost@example.com", "email_verified": True}
        )
        request = RequestFactory().get("/")

        response = SocialAccountAdapter().pre_social_login(request, sociallogin)

        assert response is not None
        assert response.status_code == 401
        assert not User.objects.filter(email="ghost@example.com").exists()

    def test_no_email_in_extra_data_returns_401(self):
        sociallogin = FakeSocialLogin(
            extra_data={"sub": "1234", "email_verified": True}
        )
        request = RequestFactory().get("/")

        response = SocialAccountAdapter().pre_social_login(request, sociallogin)

        assert response is not None
        assert response.status_code == 401

    def test_existing_user_not_group_synced_when_jit_flag_off(self):
        user = User.objects.create_user(email="bob@example.com", password="pw")
        sociallogin = FakeSocialLogin(
            extra_data={
                "email": "bob@example.com",
                "email_verified": True,
                "groups": ["Engineering"],
            }
        )
        request = RequestFactory().get("/")

        SocialAccountAdapter().pre_social_login(request, sociallogin)

        user.refresh_from_db()
        assert list(user.idp_groups.all()) == []
        assert not IdPGroup.objects.filter(name="Engineering").exists()


@pytest.mark.django_db
class TestOIDCEmailVerification:
    """An OIDC email is accepted on the IdP's own word only: an explicit false
    rejects, an explicit true accepts, silence needs the operator's trust
    switch."""

    @pytest.mark.parametrize(
        "extra_data",
        [
            {"email": "alice@example.com", "email_verified": False},
            {"email": "alice@example.com", "email_verified": "false"},
            {"userinfo": {"email": "alice@example.com", "email_verified": False}},
            {"email": "alice@example.com", "id_token": {"email_verified": False}},
            {"email": "alice@example.com", "xms_edov": False},
            # userinfo vouches, the id_token does not: the refusal wins
            {
                "userinfo": {"email": "alice@example.com", "email_verified": True},
                "id_token": {"email_verified": False},
            },
        ],
    )
    def test_explicitly_unverified_email_is_refused(self, extra_data):
        User.objects.create_user(email="alice@example.com", password="pw")
        # the trust switch never overrides an explicit refusal
        _make_sso_settings(trust_unverified_email=True)
        sociallogin = FakeSocialLogin(extra_data=extra_data)

        with pytest.raises(ValidationError) as exc:
            SocialAccountAdapter().pre_social_login(
                RequestFactory().get("/"), sociallogin
            )

        assert exc.value.code == "ssoEmailNotVerified"
        sociallogin.connect.assert_not_called()

    def test_unusable_claim_value_is_refused_not_guessed(self):
        User.objects.create_user(email="alice@example.com", password="pw")
        sociallogin = FakeSocialLogin(
            extra_data={"email": "alice@example.com", "email_verified": "maybe"}
        )

        with pytest.raises(ValidationError) as exc:
            SocialAccountAdapter().pre_social_login(
                RequestFactory().get("/"), sociallogin
            )

        assert exc.value.code == "ssoEmailNotVerified"

    def test_entra_xms_edov_true_counts_as_verified(self):
        user = User.objects.create_user(email="alice@example.com", password="pw")
        sociallogin = FakeSocialLogin(
            extra_data={"id_token": {"email": "alice@example.com", "xms_edov": True}}
        )
        request = RequestFactory().get("/")

        SocialAccountAdapter().pre_social_login(request, sociallogin)

        sociallogin.connect.assert_called_once_with(request, user)

    def test_missing_claim_is_refused_by_default(self):
        User.objects.create_user(email="alice@example.com", password="pw")
        sociallogin = FakeSocialLogin(extra_data={"email": "alice@example.com"})

        with pytest.raises(ValidationError) as exc:
            SocialAccountAdapter().pre_social_login(
                RequestFactory().get("/"), sociallogin
            )

        assert exc.value.code == "ssoEmailVerificationClaimMissing"
        sociallogin.connect.assert_not_called()

    def test_missing_claim_is_accepted_with_trust_switch(self):
        user = User.objects.create_user(email="alice@example.com", password="pw")
        _make_sso_settings(trust_unverified_email=True)
        sociallogin = FakeSocialLogin(extra_data={"email": "alice@example.com"})
        request = RequestFactory().get("/")

        SocialAccountAdapter().pre_social_login(request, sociallogin)

        sociallogin.connect.assert_called_once_with(request, user)

    def test_jit_refuses_missing_claim_by_default(self):
        _make_sso_settings(jit_provisioning_enabled=True)
        _set_feature_flag("jit_provisioning", True)
        sociallogin = FakeSocialLogin(extra_data={"email": "new.user@example.com"})

        with pytest.raises(ValidationError):
            SocialAccountAdapter().pre_social_login(
                RequestFactory().get("/"), sociallogin
            )

        assert not User.objects.filter(email="new.user@example.com").exists()

    def test_jit_provisions_missing_claim_with_trust_switch(self):
        _make_sso_settings(jit_provisioning_enabled=True, trust_unverified_email=True)
        _set_feature_flag("jit_provisioning", True)
        sociallogin = FakeSocialLogin(extra_data={"email": "new.user@example.com"})

        SocialAccountAdapter().pre_social_login(RequestFactory().get("/"), sociallogin)

        assert User.objects.filter(
            email="new.user@example.com", is_jit_provisioned=True
        ).exists()

    def test_saml_is_not_subject_to_the_oidc_rule(self):
        _make_sso_settings(provider="saml")
        sociallogin = FakeSocialLogin(
            extra_data={"urn:oid:0.9.2342.19200300.100.1.3": ["alice@example.com"]},
            provider="saml",
        )

        # No verification claim and no trust switch would refuse an OIDC login
        # here; SAML identity is resolved by the SAML ACS view instead.
        SocialAccountAdapter().pre_social_login(RequestFactory().get("/"), sociallogin)


@pytest.mark.django_db
class TestOIDCPreSSOJitProvisioning:
    def test_jit_creates_user_with_expected_fields(self):
        group = UserGroup.objects.create(name="Analysts")
        _make_sso_settings(
            jit_provisioning_enabled=True, default_user_groups=[str(group.id)]
        )
        _set_feature_flag("jit_provisioning", True)

        sociallogin = FakeSocialLogin(
            extra_data={"email": "new.user@example.com", "email_verified": True},
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
            extra_data={
                "email": "new.user@example.com",
                "email_verified": True,
                "groups": ["Engineering"],
            },
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
            extra_data={
                "email": "carol@example.com",
                "email_verified": True,
                "groups": ["Sales"],
            }
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
            extra_data={
                "email": "dora@example.com",
                "email_verified": True,
                "groups": [],
            }
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
            extra_data={
                "email": "eve@example.com",
                "email_verified": True,
                "groups": ["Something Else"],
            }
        )
        request = RequestFactory().get("/")

        SocialAccountAdapter().pre_social_login(request, sociallogin)

        user.refresh_from_db()
        assert list(user.idp_groups.all()) == [scim_group]
        assert not IdPGroup.objects.filter(name="Something Else").exists()
