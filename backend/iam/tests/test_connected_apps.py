import secrets
from datetime import timedelta

import pytest
from allauth.idp.oidc.models import Client, Token
from django.utils import timezone
from knox.models import AuthToken

from iam.models import ConnectedAppUse, User
from mcp_server.oauth import verify

pytestmark = pytest.mark.django_db

LIST_URL = "/api/iam/connected-apps/"
COPILOT_REDIRECT = "https://global.consent.azure-apim.net/redirect/new-abc"


def _user(email):
    return User.objects._create_user(
        email=email, password=None, mailing=False, initial_group=None
    )


def _client(name="Credential Manager", self_registered=True):
    client = Client(
        name=name,
        type=Client.Type.PUBLIC,
        data={"dcr": True} if self_registered else None,
    )
    client.set_redirect_uris([COPILOT_REDIRECT])
    client.save()
    return client


def _token(client, user, type=Token.Type.ACCESS_TOKEN, scopes=("mcp:read",), **kw):
    raw = secrets.token_urlsafe(32)
    token = Token(
        type=type,
        client=client,
        user=user,
        expires_at=kw.get("expires_at", timezone.now() + timedelta(hours=1)),
    )
    token.set_value(raw)
    token.set_scopes(list(scopes))
    token.save()
    return raw


@pytest.fixture
def me():
    return _user("me@example.com")


@pytest.fixture
def api(client, me):
    client.defaults["HTTP_AUTHORIZATION"] = (
        f"Token {AuthToken.objects.create(user=me)[1]}"
    )
    return client


def test_lists_apps_with_live_tokens(api, me):
    copilot = _client()
    _token(copilot, me, scopes=("openid", "mcp:read"))
    _token(copilot, me, type=Token.Type.REFRESH_TOKEN, scopes=("mcp:write",))

    apps = api.get(LIST_URL).json()

    assert len(apps) == 1
    assert apps[0]["client_id"] == copilot.id
    assert apps[0]["self_registered"] is True
    assert apps[0]["redirect_hosts"] == ["global.consent.azure-apim.net"]
    assert apps[0]["scopes"] == ["mcp:read", "mcp:write", "openid"]


def test_last_used_is_set_by_an_mcp_call(api, me):
    copilot = _client()
    raw = _token(copilot, me)
    assert api.get(LIST_URL).json()[0]["last_used_at"] is None

    verify(raw)

    assert api.get(LIST_URL).json()[0]["last_used_at"] is not None


def test_last_used_is_written_at_most_once_a_minute(me):
    copilot = _client()
    ConnectedAppUse.record(me.pk, copilot.pk)
    first = ConnectedAppUse.objects.get().last_used_at

    ConnectedAppUse.record(me.pk, copilot.pk)

    assert ConnectedAppUse.objects.get().last_used_at == first


def test_leaves_out_expired_other_users_and_service_accounts(api, me):
    expired = _client(name="Expired")
    _token(expired, me, expires_at=timezone.now() - timedelta(seconds=1))
    _token(_client(name="Not mine"), _user("other@example.com"))
    _token(_client(name="Service account"), None)

    assert api.get(LIST_URL).json() == []


def test_revoke_cuts_mcp_access(api, me):
    copilot = _client()
    raw = _token(copilot, me)
    _token(copilot, me, type=Token.Type.REFRESH_TOKEN)
    assert verify(raw) is not None

    response = api.delete(f"{LIST_URL}{copilot.id}/")

    assert response.status_code == 204
    assert verify(raw) is None
    assert api.get(LIST_URL).json() == []
    assert not ConnectedAppUse.objects.filter(user=me).exists()


def test_revoke_keeps_other_users_tokens(api, me):
    copilot = _client()
    _token(copilot, me)
    theirs = _token(copilot, _user("other@example.com"))

    api.delete(f"{LIST_URL}{copilot.id}/")

    assert verify(theirs) is not None


def test_revoke_unknown_app_is_404(api):
    assert api.delete(f"{LIST_URL}nope/").status_code == 404
