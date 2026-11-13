import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlsplit

import pytest
from allauth.idp.oidc.models import Client
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import override_settings
from knox.models import AuthToken

from iam.models import User
from iam.oidc_adapter import CISOOIDCAdapter, mcp_resource

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("mcp_on")]

AUTHORIZE_URL = "/api/identity/o/authorize"
TOKEN_URL = "/api/identity/o/api/token"
REGISTER_URL = "/api/identity/o/api/clients"
REDIRECT_URI = "http://localhost:9999/callback"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


@pytest.fixture
def knox_token():
    user = User.objects._create_user(
        email="dcr@example.com",
        password=None,
        mailing=False,
        initial_group=None,
        can_connect_apps=True,
    )
    return AuthToken.objects.create(user=user)[1]


def _make_client(self_registered: bool, skip_consent: bool = True) -> Client:
    client = Client(
        name="Test client",
        type=Client.Type.PUBLIC,
        skip_consent=skip_consent,
        data={"dcr": True} if self_registered else None,
    )
    client.set_redirect_uris([REDIRECT_URI])
    client.set_scopes(["openid", "mcp"])
    client.save()
    return client


def _authorize_params(
    oauth_client, challenge: str, resource=None, scope="openid mcp"
) -> dict:
    params = {
        "response_type": "code",
        "client_id": oauth_client.id,
        "redirect_uri": REDIRECT_URI,
        "scope": scope,
        "state": "xyz",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if resource:
        params["resource"] = resource
    return params


def _access_token(
    client, oauth_client, knox_token, resource=None, scope="openid mcp"
) -> str:
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    client.cookies["token"] = knox_token
    response = client.get(
        AUTHORIZE_URL, _authorize_params(oauth_client, challenge, resource, scope)
    )
    code = parse_qs(urlsplit(response["Location"]).query)["code"][0]
    del client.cookies["token"]
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": oauth_client.id,
        "code_verifier": verifier,
    }
    if resource:
        data["resource"] = resource
    return client.post(TOKEN_URL, data).json()["access_token"]


def _register(client: Client) -> None:
    CISOOIDCAdapter().validate_client_registration(
        client=client, client_metadata={}, token=None, bearer_token=None
    )


def _unsaved_client(*redirect_uris: str) -> Client:
    client = Client(name="DCR client", type=Client.Type.PUBLIC)
    client.set_redirect_uris(list(redirect_uris))
    client.set_scopes(["openid"])
    return client


def test_registration_endpoint_is_off_by_default(client):
    response = client.post(REGISTER_URL, {}, content_type="application/json")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "uri",
    [
        "https://app.example.com/cb",
        "http://127.0.0.1:8765/cb",
        "http://localhost:9999/cb",
    ],
)
def test_https_and_loopback_redirects_are_accepted(uri):
    _register(_unsaved_client(uri))


@pytest.mark.parametrize(
    "uri",
    [
        "http://evil.example/cb",
        "javascript:alert(1)",
        "myapp://cb",
        "https://[invalid/cb",
        "https:///callback",
        # browsers read \ as a path separator: the code would go to evil.example
        "http://evil.example\\@localhost/cb",
        "https://evil.example\\@app.example.com/cb",
    ],
)
def test_other_redirects_are_rejected(uri):
    with pytest.raises(ValidationError):
        _register(_unsaved_client(uri))


@override_settings(OAUTH_DCR_ALLOWED_REDIRECT_HOSTS=["global.consent.azure-apim.net"])
def test_redirect_host_allowlist_is_enforced():
    _register(_unsaved_client("https://global.consent.azure-apim.net/redirect"))
    with pytest.raises(ValidationError):
        _register(_unsaved_client("https://app.example.com/cb"))
    with pytest.raises(ValidationError):
        _register(
            _unsaved_client("https://evil.example\\@global.consent.azure-apim.net/cb")
        )


def test_registration_forces_mcp_scopes():
    client = _unsaved_client("https://app.example.com/cb")
    _register(client)
    assert client.get_scopes() == ["openid", "mcp"]


def test_unknown_resource_does_not_issue_a_code(client, knox_token):
    oauth_client = _make_client(self_registered=True)
    client.cookies["token"] = knox_token
    response = client.get(
        AUTHORIZE_URL,
        _authorize_params(oauth_client, "x" * 43, "https://other.example/api"),
    )
    assert "code=" not in response.get("Location", "")


def test_mcp_resource_is_accepted(client, knox_token):
    oauth_client = _make_client(self_registered=True)
    assert _access_token(client, oauth_client, knox_token, resource=mcp_resource())


def test_a_self_registered_token_without_the_mcp_scope_is_refused(client, knox_token):
    token = _access_token(
        client, _make_client(self_registered=True), knox_token, scope="openid"
    )
    response = client.get("/api/folders/", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert response.status_code in (401, 403)


def test_admin_registered_token_still_works_on_rest_api(client, knox_token):
    token = _access_token(
        client, _make_client(self_registered=False), knox_token, scope="openid"
    )
    response = client.get("/api/folders/", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert response.status_code == 200


def test_an_mcp_token_reaches_only_what_the_tools_use(client, knox_token):
    # whoever presents it, an app or the MCP server, on the backend's one port
    token = _access_token(client, _make_client(self_registered=True), knox_token)
    auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    assert client.get("/api/folders/", **auth).status_code == 200
    assert client.get("/api/iam/auth-tokens/", **auth).status_code == 403


def test_consent_page_warns_about_self_registered_clients(client, knox_token):
    oauth_client = _make_client(self_registered=True, skip_consent=False)
    client.cookies["token"] = knox_token
    response = client.get(AUTHORIZE_URL, _authorize_params(oauth_client, "x" * 43))
    assert response.status_code == 200
    assert b"You are adding a new app." in response.content
    assert REDIRECT_URI.encode() in response.content


@pytest.mark.parametrize(
    "configured, sent",
    [
        # clients drop the default port: WHATWG URL and pydantic both do
        ("https://grc.example.com:443", "https://grc.example.com/mcp"),
        ("http://grc.example.com:80", "http://grc.example.com/mcp"),
        ("https://grc.example.com", "https://grc.example.com:443/mcp"),
        ("https://GRC.example.com/", "https://grc.example.com/mcp"),
    ],
)
def test_the_mcp_resource_ignores_the_default_port(
    client, knox_token, settings, configured, sent
):
    settings.CISO_ASSISTANT_URL = configured
    token = _access_token(
        client, _make_client(self_registered=True), knox_token, resource=sent
    )
    response = client.get("/api/folders/", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "resource",
    [
        # a resource has no user and no fragment (RFC 8707): refused, not cleaned
        "https://evil@{host}/mcp",
        "https://user:pass@{host}/mcp",
        "https://@{host}/mcp",
        "https://{host}/mcp#x",
        "https://{host}\\@other.example/mcp",
        "https://{host}/mcp?x=1",
    ],
)
def test_a_lookalike_mcp_resource_does_not_issue_a_code(
    client, knox_token, settings, resource
):
    settings.CISO_ASSISTANT_URL = "https://grc.example.com:443"
    client.cookies["token"] = knox_token
    response = client.get(
        AUTHORIZE_URL,
        _authorize_params(
            _make_client(self_registered=True),
            "x" * 43,
            resource.format(host="grc.example.com"),
        ),
    )
    assert "code=" not in response.get("Location", "")
