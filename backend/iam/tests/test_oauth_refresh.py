import base64
import hashlib
import secrets
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from allauth.idp.oidc.models import Client, Token
from django.test import override_settings
from django.utils import timezone
from knox.models import AuthToken

from iam.models import User

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("mcp_on")]

AUTHORIZE_URL = "/api/identity/o/authorize"
TOKEN_URL = "/api/identity/o/api/token"
REDIRECT_URI = "http://localhost:9999/callback"
THIRTY_DAYS = 30 * 24 * 3600


@pytest.fixture
def app():
    client = Client(name="Test client", type=Client.Type.PUBLIC, skip_consent=True)
    client.set_redirect_uris([REDIRECT_URI])
    client.set_grant_types(
        [Client.GrantType.AUTHORIZATION_CODE, Client.GrantType.REFRESH_TOKEN]
    )
    client.save()
    return client


def _sign_in(http, app):
    user = User.objects._create_user(
        email="u@example.com",
        password=None,
        mailing=False,
        initial_group=None,
        can_connect_apps=True,
    )
    http.cookies["token"] = AuthToken.objects.create(user=user)[1]
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    response = http.get(
        AUTHORIZE_URL,
        {
            "response_type": "code",
            "client_id": app.id,
            "redirect_uri": REDIRECT_URI,
            "scope": "openid",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    code = parse_qs(urlsplit(response["Location"]).query)["code"][0]
    return http.post(
        TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "client_id": app.id,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
        },
    ).json()


def _refresh(http, app, refresh_token):
    return http.post(
        TOKEN_URL,
        {
            "grant_type": "refresh_token",
            "client_id": app.id,
            "refresh_token": refresh_token,
        },
    )


def _refresh_token_row():
    return Token.objects.get(type=Token.Type.REFRESH_TOKEN)


@override_settings(IDP_OIDC_REFRESH_TOKEN_EXPIRES_IN=THIRTY_DAYS)
def test_each_refresh_restarts_the_idle_limit(client, app):
    first = _sign_in(client, app)

    second = _refresh(client, app, first["refresh_token"]).json()

    assert second["refresh_token"] != first["refresh_token"]
    left = _refresh_token_row().expires_at - timezone.now()
    assert timedelta(days=29) < left <= timedelta(days=30)


@override_settings(IDP_OIDC_REFRESH_TOKEN_EXPIRES_IN=THIRTY_DAYS)
def test_an_idle_refresh_token_is_refused(client, app):
    tokens = _sign_in(client, app)
    Token.objects.filter(type=Token.Type.REFRESH_TOKEN).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    response = _refresh(client, app, tokens["refresh_token"])

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_grant"
