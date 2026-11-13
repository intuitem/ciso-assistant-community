from unittest.mock import MagicMock, patch

import pytest
from allauth.socialaccount.models import SocialAccount
from django.http import HttpRequest
from django.test import Client
from django.urls import reverse

from global_settings.models import GlobalSettings
from iam.models import User

EMAIL_URI = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
EMAIL_OID = "urn:oid:0.9.2342.19200300.100.1.3"
NAMEID_UNSPECIFIED = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
NAMEID_EMAIL = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"


def _make_sso_settings(email_mapping):
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.SSO,
        defaults={
            "value": {
                "is_enabled": True,
                "provider": "saml",
                "provider_id": "test-saml",
                "name": "Test SAML",
                "client_id": "default",
                "settings": {
                    "attribute_mapping": {"email": email_mapping},
                    "advanced": {"reject_idp_initiated_sso": False},
                },
            }
        },
    )


def _make_auth(nameid, attributes, nameid_format=NAMEID_UNSPECIFIED):
    auth = MagicMock()
    auth.process_response.return_value = None
    auth.get_errors.return_value = []
    auth.is_authenticated.return_value = True
    auth.get_last_response_in_response_to.return_value = None
    auth.get_nameid.return_value = nameid
    auth.get_nameid_format.return_value = nameid_format
    auth.get_attributes.return_value = attributes
    auth.get_attribute.side_effect = lambda name: attributes.get(name)
    return auth


def _finish_acs(auth):
    session = MagicMock()
    session.store = {"request": "dummy"}
    with (
        patch("iam.sso.saml.views.build_auth", return_value=auth),
        patch("iam.sso.saml.views.LoginSession", return_value=session),
        patch(
            "iam.sso.saml.views.httpkit.deserialize_request",
            return_value=HttpRequest(),
        ),
        patch("iam.sso.saml.views.stash_saml_slo_state"),
    ):
        url = reverse("saml_finish_acs", kwargs={"organization_slug": "default"})
        return Client().get(url)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "email_mapping,attributes,nameid_format",
    [
        # Mapping set through the API, one attribute name per item.
        ([EMAIL_URI], {EMAIL_URI: ["jane@example.com"]}, NAMEID_UNSPECIFIED),
        # Mapping edited in the settings form: the list is edited as one text
        # field and saved back as a single comma-joined name.
        (
            [f"{EMAIL_OID},{EMAIL_URI}"],
            {EMAIL_URI: ["jane@example.com"]},
            NAMEID_UNSPECIFIED,
        ),
        (
            [f"{EMAIL_OID},{EMAIL_URI}"],
            {"mail": ["jane@example.com"]},
            NAMEID_UNSPECIFIED,
        ),
        ([f"{EMAIL_OID},{EMAIL_URI}"], {EMAIL_URI: ["jane@example.com"]}, NAMEID_EMAIL),
    ],
    ids=[
        "api-mapping",
        "form-mapping",
        "form-mapping-mail-attr",
        "form-mapping-email-nameid",
    ],
)
def test_saml_login_links_social_account(email_mapping, attributes, nameid_format):
    user = User.objects.create_user(email="jane@example.com")
    _make_sso_settings(email_mapping)

    response = _finish_acs(_make_auth("jane@example.com", attributes, nameid_format))

    assert response.status_code == 302
    assert "error" not in response.url
    assert SocialAccount.objects.filter(user=user, provider="test-saml").exists()
    user.refresh_from_db()
    assert user.is_sso


@pytest.mark.django_db
def test_saml_login_reuses_linked_social_account():
    user = User.objects.create_user(email="jane@example.com")
    _make_sso_settings([f"{EMAIL_OID},{EMAIL_URI}"])
    auth = _make_auth("jane@example.com", {EMAIL_URI: ["jane@example.com"]})

    _finish_acs(auth)
    response = _finish_acs(auth)

    assert "error" not in response.url
    assert SocialAccount.objects.filter(user=user).count() == 1
