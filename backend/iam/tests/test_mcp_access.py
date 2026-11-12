import base64
import hashlib
import secrets
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from allauth.idp.oidc.models import Client, Token
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone
from knox.models import AuthToken
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from core.serializers import UserWriteSerializer
from core.startup import startup
from iam.mcp_access import mcp_access_for as verify
from iam.models import AppGrant, ConnectedAppUse, ConnectionProfile, User, UserGroup
from iam.oidc_adapter import CISOOIDCAdapter, mcp_resource

pytestmark = pytest.mark.django_db

AUTHORIZE_URL = "/api/identity/o/authorize"
APPS_URL = "/api/iam/connected-apps/"
REDIRECT_URI = "http://localhost:9999/callback"
COPILOT_REDIRECT = "https://global.consent.azure-apim.net/redirect/abc"
ISSUER = settings.CISO_ASSISTANT_URL.rstrip("/") + "/api"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


def _user(email, allowed=True):
    return User.objects._create_user(
        email=email,
        password=None,
        mailing=False,
        initial_group=None,
        can_connect_apps=allowed,
    )


def _client(
    name="Credential Manager",
    self_registered=True,
    redirect=REDIRECT_URI,
    skip_consent=True,
):
    client = Client(
        name=name,
        type=Client.Type.PUBLIC,
        skip_consent=skip_consent,
        data={"dcr": True} if self_registered else None,
    )
    client.set_redirect_uris([redirect])
    client.set_scopes(["openid", "mcp"])
    client.save()
    return client


def _token(client, user, type=Token.Type.ACCESS_TOKEN, scopes=("mcp",)):
    raw = secrets.token_urlsafe(32)
    token = Token(
        type=type,
        client=client,
        user=user,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    token.set_value(raw)
    token.set_scopes(list(scopes))
    if "mcp" in scopes:
        token.set_resources([mcp_resource()])
    token.save()
    if user is not None and "mcp" in scopes:
        ConnectionProfile.sync_builtin()
        AppGrant.consent(
            user.pk, client.pk, ConnectionProfile.matching(True, True, True)
        )
    return raw


def _authorize(http, client, user, scope="openid mcp", prompt=None, resource=None):
    challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(secrets.token_urlsafe(48).encode()).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    params = {
        "response_type": "code",
        "client_id": client.id,
        "redirect_uri": REDIRECT_URI,
        "scope": scope,
        "state": "xyz",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if prompt:
        params["prompt"] = prompt
    if resource:
        params["resource"] = resource
    http.cookies["token"] = AuthToken.objects.create(user=user)[1]
    return http.get(AUTHORIZE_URL, params)


# ---------------------------------------------------------------- kill switch


class TestKillSwitchOff:
    def test_registration_is_refused(self):
        unsaved = Client(name="Credential Manager", type=Client.Type.PUBLIC)
        unsaved.set_redirect_uris([COPILOT_REDIRECT])
        with pytest.raises(ValidationError, match="MCP is disabled"):
            CISOOIDCAdapter().validate_client_registration(client=unsaved)

    def test_mcp_consent_is_refused(self, client):
        response = _authorize(client, _client(), _user("u@example.com"))
        assert response.status_code == 403
        assert b"has not enabled AI app connections" in response.content

    def test_mcp_tokens_are_refused(self):
        raw = _token(_client(), _user("u@example.com"))
        assert verify(raw) is None

    def test_existing_connections_come_back_when_turned_on(self, request):
        raw = _token(_client(), _user("u@example.com"))
        assert verify(raw) is None
        request.getfixturevalue("mcp_on")
        assert verify(raw) is not None

    def test_does_not_block_a_non_mcp_app(self, client):
        response = _authorize(
            client, _client(self_registered=False), _user("u@example.com"), "openid"
        )
        assert response.status_code == 302
        assert "code" in parse_qs(urlsplit(response["Location"]).query)


# ---------------------------------------------------------------- per-user flag


@pytest.mark.usefixtures("mcp_on")
class TestUserNotAllowed:
    def test_consent_is_refused_with_a_way_back(self, client):
        response = _authorize(client, _client(), _user("no@example.com", False))
        assert response.status_code == 403
        assert b"has not allowed your account" in response.content
        back = response.context["back_url"]
        query = parse_qs(urlsplit(back).query)
        assert back.startswith(REDIRECT_URI)
        assert query["error"] == ["access_denied"]
        assert query["state"] == ["xyz"]
        assert query["iss"] == [ISSUER]

    def test_prompt_none_gets_no_code(self, client):
        response = _authorize(
            client, _client(), _user("no@example.com", False), prompt="none"
        )
        query = parse_qs(urlsplit(response.get("Location", "")).query)
        assert "code" not in query
        assert not Token.objects.filter(type=Token.Type.AUTHORIZATION_CODE).exists()

    def test_mcp_tokens_are_refused(self):
        user = _user("no@example.com", False)
        assert verify(_token(_client(), user)) is None
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(_client(), user)}")
        assert api.get("/api/folders/").status_code == 401

    def test_other_apps_do_not_need_it(self, client):
        # existing admin-registered apps keep working without the flag
        user = _user("no@example.com", False)
        raw = _token(_client(self_registered=False), user, scopes=("openid",))
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
        assert api.get("/api/folders/").status_code == 200
        response = _authorize(client, _client(self_registered=False), user, "openid")
        assert "code" in parse_qs(urlsplit(response["Location"]).query)

    def test_other_users_are_unaffected(self):
        _user("no@example.com", False)
        assert verify(_token(_client(), _user("yes@example.com"))) is not None

    def test_new_users_are_not_allowed_by_default(self):
        user = User.objects._create_user(
            email="new@example.com", password=None, mailing=False, initial_group=None
        )
        assert user.can_connect_apps is False


@pytest.mark.usefixtures("mcp_on")
class TestLosingAccess:
    def test_unticking_deletes_the_mcp_connections(self):
        user = _user("u@example.com")
        app, other = _client(), _client(name="Internal tool", self_registered=False)
        raw = _token(app, user)
        _token(app, user, type=Token.Type.REFRESH_TOKEN)
        _token(app, user, type=Token.Type.AUTHORIZATION_CODE)
        ConnectedAppUse.record(user.pk, app.pk)
        _token(other, user, scopes=("openid",))

        user.can_connect_apps = False
        user.save()

        assert not Token.objects.filter(user=user, client=app).exists()
        assert not ConnectedAppUse.objects.filter(user=user, client=app).exists()
        assert Token.objects.filter(user=user, client=other).exists()
        user.can_connect_apps = True
        user.save()
        assert verify(raw) is None

    def test_deactivating_deletes_every_token(self):
        user = _user("u@example.com")
        _token(_client(), user)
        _token(
            _client(name="Internal tool", self_registered=False),
            user,
            scopes=("openid",),
        )
        user.is_active = False
        user.save()
        assert not Token.objects.filter(user=user).exists()

    def test_unrelated_saves_keep_tokens(self):
        user = _user("u@example.com")
        _token(_client(), user)
        user.first_name = "Alice"
        user.save()
        user.save(update_fields=["last_login"])
        assert Token.objects.filter(user=user).exists()

    def test_an_expired_connection_needs_consent_again(self, client):
        # the idle limit passed: every token of the app expired, its grant stayed
        user, expired = _user("u@example.com"), _client(name="Expired")
        _token(expired, user, type=Token.Type.REFRESH_TOKEN)
        Token.objects.filter(client=expired).update(
            expires_at=timezone.now() - timedelta(days=1)
        )
        # a live connection to another app, which allauth alone would accept
        _token(_client(name="Other"), user, scopes=("openid", "mcp"))

        response = _authorize(client, expired, user, prompt="none")

        query = parse_qs(urlsplit(response["Location"]).query)
        assert "code" not in query
        assert query["error"] == ["consent_required"]

    def test_a_live_token_without_mcp_does_not_restore_the_connection(self, client):
        # the app's MCP tokens expired, but it still holds a live openid token,
        # and another app holds a live MCP token for the same user
        user, app = _user("u@example.com"), _client(name="Expired")
        _token(app, user, type=Token.Type.REFRESH_TOKEN)
        Token.objects.filter(client=app).update(
            expires_at=timezone.now() - timedelta(days=1)
        )
        _token(app, user, scopes=("openid",))
        _token(_client(name="Other"), user, scopes=("openid", "mcp"))

        response = _authorize(client, app, user, prompt="none")

        query = parse_qs(urlsplit(response["Location"]).query)
        assert "code" not in query
        assert query["error"] == ["consent_required"]

    def test_a_silent_request_for_mcp_without_the_scope_gets_no_code(self, client):
        # approved before with the scope added by the consent page; silently,
        # that page is skipped and the code would carry openid only
        user, app = _user("u@example.com"), _client()
        _token(app, user, scopes=("openid", "mcp"))

        response = _authorize(
            client, app, user, scope="openid", prompt="none", resource=mcp_resource()
        )

        query = parse_qs(urlsplit(response["Location"]).query)
        assert "code" not in query
        assert query["error"] == ["consent_required"]

    def test_only_an_admin_may_change_the_flag(self):
        target = _user("target@example.com", False)
        request = SimpleNamespace(user=_user("manager@example.com"))
        serializer = UserWriteSerializer(
            target,
            data={"can_connect_apps": True},
            partial=True,
            context={"request": request},
        )
        with pytest.raises(PermissionDenied):
            serializer.is_valid(raise_exception=True)


@pytest.mark.usefixtures("mcp_on")
def test_consent_records_the_authorization_date(client):
    user, app = _user("u@example.com"), _client()
    response = _authorize(client, app, user)
    assert "code" in parse_qs(urlsplit(response["Location"]).query)
    use = ConnectedAppUse.objects.get(user=user, client=app)
    assert use.authorized_at is not None
    assert use.last_used_at is None


# ---------------------------------------------------------------- admin list


@pytest.fixture
def admin_api():
    startup(sender=None)
    admin = User.objects.create_superuser("admin@example.com")
    group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = group.folder
    admin.save()
    group.user_set.add(admin)
    api = APIClient()
    api.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=admin)[1]}"
    )
    return api


@pytest.mark.usefixtures("mcp_on")
class TestAdminList:
    def test_lists_everyones_connections(self, admin_api):
        alice, bruno = _user("alice@example.com"), _user("bruno@example.com")
        _token(_client(redirect=COPILOT_REDIRECT), alice)
        _token(_client(name="Claude Code"), bruno)

        rows = admin_api.get(f"{APPS_URL}all/").json()["results"]

        assert {(r["user"]["email"], r["name"]) for r in rows} == {
            ("alice@example.com", "Credential Manager"),
            ("bruno@example.com", "Claude Code"),
        }

    def test_filters(self, admin_api):
        alice, bruno = _user("alice@example.com"), _user("bruno@example.com")
        _token(_client(), alice)
        _token(_client(name="Internal tool", self_registered=False), bruno)

        assert [
            r["user"]["email"]
            for r in admin_api.get(f"{APPS_URL}all/?search=bruno").json()["results"]
        ] == ["bruno@example.com"]
        assert [
            r["name"]
            for r in admin_api.get(f"{APPS_URL}all/?self_registered=true").json()[
                "results"
            ]
        ] == ["Credential Manager"]

    def test_is_paginated(self, admin_api):
        app = _client()
        for i in range(3):
            _token(app, _user(f"user{i}@example.com"))

        body = admin_api.get(f"{APPS_URL}all/?limit=2").json()

        assert body["count"] == 3
        assert len(body["results"]) == 2
        assert body["next"] is not None
        rest = admin_api.get(body["next"]).json()["results"]
        assert len(rest) == 1

    def test_is_for_admins_only(self):
        api = APIClient()
        user = _user("u@example.com")
        api.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
        )
        assert api.get(f"{APPS_URL}all/").status_code == 403

    def test_revoking_one_connection_keeps_the_others(self, admin_api):
        alice, bruno = _user("alice@example.com"), _user("bruno@example.com")
        app, other = _client(), _client(name="Claude Code")
        cut = _token(app, alice)
        kept_other_app = _token(other, alice)
        kept_other_user = _token(app, bruno)

        response = admin_api.delete(f"{APPS_URL}all/{alice.id}/{app.id}/")

        assert response.status_code == 204
        assert verify(cut) is None
        assert verify(kept_other_app) is not None
        assert verify(kept_other_user) is not None


@pytest.mark.usefixtures("mcp_on")
class TestRevokeForEveryone:
    def test_counts_the_users_of_the_selected_app_only(self, admin_api):
        # a registration with the same name and host is not the same app: the
        # name is chosen by the app itself
        selected = _client(redirect=COPILOT_REDIRECT)
        same_name = _client(redirect=COPILOT_REDIRECT)
        alice = _user("alice@example.com")
        _token(selected, alice)
        _token(selected, _user("bruno@example.com"))
        _token(same_name, alice)

        summary = admin_api.get(f"{APPS_URL}apps/{selected.id}/").json()

        assert summary["users"] == 2
        assert "registrations" not in summary

    def test_revokes_and_deletes_the_selected_app_only(self, admin_api):
        selected = _client(redirect=COPILOT_REDIRECT)
        same_name = _client(redirect=COPILOT_REDIRECT)
        alice, bruno = _user("alice@example.com"), _user("bruno@example.com")
        cut = [_token(selected, alice), _token(selected, bruno)]
        kept = _token(same_name, alice)

        response = admin_api.delete(f"{APPS_URL}apps/{selected.id}/")

        assert response.json() == {"users": 2}
        assert not Client.objects.filter(id=selected.id).exists()
        assert Client.objects.filter(id=same_name.id).exists()
        assert all(verify(raw) is None for raw in cut)
        assert verify(kept) is not None

    def test_counts_only_users_still_connected(self, admin_api):
        # Bruno's connection has ended: the listing does not show him, so the
        # confirmation must not count him
        app = _client(redirect=COPILOT_REDIRECT)
        _token(app, _user("alice@example.com"))
        bruno = _user("bruno@example.com")
        _token(app, bruno)
        Token.objects.filter(client=app, user=bruno).update(
            expires_at=timezone.now() - timedelta(days=1)
        )

        summary = admin_api.get(f"{APPS_URL}apps/{app.id}/").json()
        response = admin_api.delete(f"{APPS_URL}apps/{app.id}/")

        assert summary["users"] == 1
        assert response.json() == {"users": 1}
        assert not Token.objects.filter(client_id=app.id).exists()

    def test_keeps_an_admin_registered_client(self, admin_api):
        internal = _client(name="Internal tool", self_registered=False)
        _token(internal, _user("alice@example.com"))

        admin_api.delete(f"{APPS_URL}apps/{internal.id}/")

        assert Client.objects.filter(id=internal.id).exists()
        assert not Token.objects.filter(client=internal).exists()
