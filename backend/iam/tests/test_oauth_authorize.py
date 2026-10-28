import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlsplit

import pytest
from allauth.idp.oidc.models import Client
from django.conf import settings
from knox.models import AuthToken

from iam.models import User

pytestmark = pytest.mark.django_db

AUTHORIZE_URL = "/api/identity/o/authorize"
REDIRECT_URI = "http://localhost:9999/callback"
ISSUER = settings.CISO_ASSISTANT_URL.rstrip("/") + "/api"


@pytest.fixture
def oauth_client():
    client = Client(name="Test client", type=Client.Type.PUBLIC, skip_consent=True)
    client.set_redirect_uris([REDIRECT_URI])
    client.save()
    return client


@pytest.fixture
def knox_token():
    user = User.objects._create_user(
        email="oauth@example.com", password=None, mailing=False, initial_group=None
    )
    return AuthToken.objects.create(user=user)[1]


def _params(oauth_client):
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return {
        "response_type": "code",
        "client_id": oauth_client.id,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid",
        "state": "xyz",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }


def test_anonymous_user_is_sent_to_frontend_login(client, oauth_client):
    response = client.get(AUTHORIZE_URL, _params(oauth_client))
    assert response.status_code == 302
    location = response["Location"]
    assert location.startswith(settings.CISO_ASSISTANT_URL.rstrip("/") + "/login?")
    assert parse_qs(urlsplit(location).query)["next"][0].startswith(AUTHORIZE_URL)


def test_invalid_knox_cookie_is_sent_to_login(client, oauth_client):
    client.cookies["token"] = "not-a-real-token"
    response = client.get(AUTHORIZE_URL, _params(oauth_client))
    assert "/login?" in response["Location"]


def test_logged_in_user_gets_code_and_iss(client, oauth_client, knox_token):
    client.cookies["token"] = knox_token
    response = client.get(AUTHORIZE_URL, _params(oauth_client))
    assert response.status_code == 302
    location = urlsplit(response["Location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == REDIRECT_URI
    query = parse_qs(location.query)
    assert "code" in query
    assert query["state"] == ["xyz"]
    assert query["iss"] == [ISSUER]


def test_consent_page_when_client_does_not_skip_consent(
    client, oauth_client, knox_token
):
    oauth_client.skip_consent = False
    oauth_client.save()
    client.cookies["token"] = knox_token
    response = client.get(AUTHORIZE_URL, _params(oauth_client))
    assert response.status_code == 200
    assert b"This app registered itself" not in response.content


def test_metadata_advertises_issuer_and_iss_support(client):
    data = client.get("/api/.well-known/openid-configuration").json()
    assert data["issuer"] == ISSUER
    assert data["authorization_response_iss_parameter_supported"] is True
    assert {"mcp:read", "mcp:write"} <= set(data["scopes_supported"])


def test_knox_cookie_is_not_accepted_by_the_rest_api(client, knox_token):
    client.cookies["token"] = knox_token
    assert client.get("/api/folders/").status_code in (401, 403)
