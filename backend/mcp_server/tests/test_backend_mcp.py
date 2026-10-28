import base64
import hashlib
import json
import secrets
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from allauth.idp.oidc.models import Client, Token
from django.core.cache import cache
from django.utils import timezone
from knox.models import AuthToken
from starlette.testclient import TestClient

from iam.models import User
from iam.oidc_adapter import mcp_resource
from mcp_server.oauth import PAT_CLIENT_ID, verify
from mcp_server.transport import request_as

AUTHORIZE_URL = "/api/identity/o/authorize"
TOKEN_URL = "/api/identity/o/api/token"
REDIRECT_URI = "http://localhost:9999/callback"
METADATA_PATH = "/.well-known/oauth-protected-resource/mcp"
MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


@pytest.fixture
def user():
    return User.objects._create_user(
        email="mcp@example.com", password=None, mailing=False, initial_group=None
    )


@pytest.fixture
def pat(user):
    return AuthToken.objects.create(user=user)[1]


@pytest.fixture
def app():
    # the SDK's session manager runs once per app instance
    from mcp_server.app import build_app

    return build_app()


def _oauth_token(client, knox_token, resource=None, scope="mcp:read") -> str:
    oauth_client = Client(
        name="MCP client",
        type=Client.Type.PUBLIC,
        skip_consent=True,
        data={"dcr": True},
    )
    oauth_client.set_redirect_uris([REDIRECT_URI])
    oauth_client.set_scopes(["openid", "mcp:read", "mcp:write"])
    oauth_client.save()

    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    params = {
        "response_type": "code",
        "client_id": oauth_client.id,
        "redirect_uri": REDIRECT_URI,
        "scope": scope,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    data = {
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "client_id": oauth_client.id,
        "code_verifier": verifier,
    }
    if resource:
        params["resource"] = data["resource"] = resource
    client.cookies["token"] = knox_token
    response = client.get(AUTHORIZE_URL, params)
    del client.cookies["token"]
    data["code"] = parse_qs(urlsplit(response["Location"]).query)["code"][0]
    return client.post(TOKEN_URL, data).json()["access_token"]


@pytest.mark.django_db
class TestVerifier:
    def test_token_bound_to_mcp_is_accepted(self, client, user, pat):
        raw = _oauth_token(client, pat, resource=mcp_resource())
        access = verify(raw)
        assert access is not None
        assert access.subject == str(user.pk)
        assert access.resource == mcp_resource()
        assert access.scopes == ["mcp:read"]

    def test_token_without_resource_but_mcp_scope_is_accepted(self, client, pat):
        # what Copilot Studio sends: no RFC 8707 resource parameter
        access = verify(_oauth_token(client, pat))
        assert access is not None
        assert access.resource == mcp_resource()

    def test_token_without_resource_or_mcp_scope_is_refused(self, client, pat):
        assert verify(_oauth_token(client, pat, scope="openid")) is None

    def test_expired_token_is_refused(self, client, pat):
        raw = _oauth_token(client, pat, resource=mcp_resource())
        Token.objects.filter(type=Token.Type.ACCESS_TOKEN).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        assert verify(raw) is None

    def test_token_of_inactive_user_is_refused(self, client, user, pat):
        raw = _oauth_token(client, pat, resource=mcp_resource())
        user.is_active = False
        user.save()
        assert verify(raw) is None

    def test_personal_access_token_is_accepted(self, user, pat):
        access = verify(pat)
        assert access.client_id == PAT_CLIENT_ID
        assert access.subject == str(user.pk)
        assert set(access.scopes) == {"mcp:read", "mcp:write"}

    def test_garbage_is_refused(self):
        assert verify("not-a-token") is None


@pytest.mark.django_db
class TestTransport:
    def test_read_goes_through_the_api(self, user):
        response = request_as(user, "GET", "/folders/", params={"limit": 5})
        assert response.status_code == 200
        assert "results" in response.json()

    def test_rbac_still_applies(self, user):
        response = request_as(user, "POST", "/folders/", json={"name": "Nope"})
        assert response.status_code == 403


def test_unauthenticated_call_gets_401_with_metadata_pointer(app):
    with TestClient(app, base_url="http://localhost:8001") as http:
        response = http.post("/mcp", headers=MCP_HEADERS, json={})
    assert response.status_code == 401
    assert METADATA_PATH in response.headers["www-authenticate"]


def test_protected_resource_metadata(app):
    with TestClient(app, base_url="http://localhost:8001") as http:
        metadata = http.get(METADATA_PATH).json()
    assert metadata["resource"] == mcp_resource()
    assert metadata["authorization_servers"][0].endswith("/api")
    assert "mcp:read" in metadata["scopes_supported"]


@pytest.mark.django_db(transaction=True)
def test_authorization_server_metadata_at_rfc8414_address(app):
    with TestClient(app, base_url="http://localhost:8001") as http:
        response = http.get("/.well-known/oauth-authorization-server/api")
    assert response.status_code == 200
    metadata = response.json()
    assert metadata["issuer"].endswith("/api")
    assert metadata["token_endpoint"].endswith("/api/identity/o/api/token")


@pytest.mark.django_db(transaction=True)
def test_tool_call_runs_as_the_token_user(app, pat):
    headers = {**MCP_HEADERS, "Authorization": f"Bearer {pat}"}
    call = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "get_folders", "arguments": {}},
    }
    with TestClient(app, base_url="http://localhost:8001") as http:
        response = http.post("/mcp", headers=headers, json=call)
    assert response.status_code == 200
    payload = json.loads(
        next(
            line[len("data:") :]
            for line in response.text.splitlines()
            if line.startswith("data:")
        )
    )
    assert payload["result"]["isError"] is False
