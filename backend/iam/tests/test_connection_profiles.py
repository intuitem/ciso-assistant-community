import base64
import hashlib
import secrets
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from allauth.idp.oidc.models import Client, Token
from django.core.cache import cache
from django.utils import timezone
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.startup import startup
from iam.models import AppGrant, ConnectionProfile, User, UserGroup
from iam.mcp_access import mcp_access_for as verify
from iam.oidc_adapter import mcp_resource

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("mcp_on")]

AUTHORIZE_URL = "/api/identity/o/authorize"
REDIRECT_URI = "http://localhost:9999/callback"


@pytest.fixture(autouse=True)
def _clean():
    cache.clear()
    ConnectionProfile.sync_builtin()


def _profile(create=False, update=False, delete=False):
    return ConnectionProfile.matching(create, update, delete)


def _user(email="u@example.com"):
    return User.objects._create_user(
        email=email,
        password=None,
        mailing=False,
        initial_group=None,
        can_connect_apps=True,
    )


def _client(skip_consent=False):
    client = Client(
        name="Claude Code",
        type=Client.Type.PUBLIC,
        skip_consent=skip_consent,
        data={"dcr": True},
    )
    client.set_redirect_uris([REDIRECT_URI])
    client.set_scopes(["openid", "mcp"])
    client.save()
    return client


def _token(client, user, profile=None, scopes=("mcp",)):
    raw = secrets.token_urlsafe(32)
    token = Token(
        type=Token.Type.ACCESS_TOKEN,
        client=client,
        user=user,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    token.set_value(raw)
    token.set_scopes(list(scopes))
    token.save()
    if profile is not None:
        AppGrant.consent(user.pk, client.pk, profile)
    return raw


def _authorize(http, client, user, scope="openid mcp", **extra):
    challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(secrets.token_urlsafe(48).encode()).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    http.cookies["token"] = AuthToken.objects.create(user=user)[1]
    return http.get(
        AUTHORIZE_URL,
        {
            "response_type": "code",
            "client_id": client.id,
            "redirect_uri": REDIRECT_URI,
            "scope": scope,
            "state": "xyz",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            **extra,
        },
    )


def _consent(http, page, *actions):
    signed = page.context["form"]["request"].value()
    return http.post(
        AUTHORIZE_URL,
        {
            "request": signed,
            "action": "grant",
            **{f"can_{action}": "on" for action in actions},
        },
    )


def _code(response):
    return parse_qs(urlsplit(response.get("Location", "")).query).get("code")


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


class TestConsent:
    def test_reads_only_while_writes_are_off(self, client):
        user, app = _user(), _client()

        page = _authorize(client, app, user)

        assert page.status_code == 200
        assert "scopes" not in page.context["form"].fields
        assert "write_choices" not in page.context
        assert b"allows apps to read only" in page.content
        response = _consent(client, page, "create", "delete")
        assert _code(response)
        assert AppGrant.objects.get(user=user, client=app).profile == _profile()

    @pytest.mark.usefixtures("mcp_write_on")
    def test_offers_create_update_and_delete_once_allowed(self, client):
        page = _authorize(client, _client(), _user())

        fields = [field.name for field, label in page.context["write_choices"]]
        assert fields == ["can_create", "can_update", "can_delete"]
        assert b'name="can_delete"' in page.content

    @pytest.mark.usefixtures("mcp_write_on")
    def test_the_ticked_actions_choose_the_profile(self, client):
        user, app = _user(), _client()

        response = _consent(client, _authorize(client, app, user), "create", "delete")

        assert _code(response)
        grant = AppGrant.objects.get(user=user, client=app)
        assert grant.profile.actions == ["read", "create", "delete"]

    @pytest.mark.usefixtures("mcp_write_on")
    def test_consenting_again_replaces_the_grant(self, client):
        user, app = _user(), _client()
        _consent(client, _authorize(client, app, user), "create", "update", "delete")

        _consent(client, _authorize(client, app, user))

        assert AppGrant.objects.get(user=user, client=app).profile == _profile()

    @pytest.mark.usefixtures("mcp_write_on")
    def test_skip_consent_gets_read_only(self, client):
        user, app = _user(), _client(skip_consent=True)

        response = _authorize(client, app, user)

        assert _code(response)
        assert AppGrant.objects.get(user=user, client=app).profile == _profile()

    def test_a_silent_request_without_a_grant_gets_no_code(self, client):
        response = _authorize(client, _client(), _user(), prompt="none")

        assert not _code(response)
        assert "error=consent_required" in response["Location"]
        assert not AppGrant.objects.exists()

    def test_no_profile_at_all_is_refused(self, client):
        ConnectionProfile.objects.all().delete()
        response = _authorize(client, _client(skip_consent=True), _user())

        assert response.status_code == 403
        assert b"has not set up what AI apps may do" in response.content

    def test_a_plain_sign_in_is_not_affected(self, client):
        response = _authorize(client, _client(skip_consent=True), _user(), "openid")

        assert _code(response)
        assert not AppGrant.objects.exists()


class TestTokens:
    def test_a_token_without_grant_is_refused(self):
        assert verify(_token(_client(), _user())) is None

    def test_reads_only_while_writes_are_off(self):
        access = verify(_token(_client(), _user(), _profile(True, True, False)))
        assert access.claims() == {
            "actions": ["read"],
            "profile": "Read, create and update",
            "app": "Claude Code",
        }

    @pytest.mark.usefixtures("mcp_write_on")
    def test_the_actions_come_from_the_profile(self):
        access = verify(_token(_client(), _user(), _profile(True, True, False)))
        assert access.actions == ["read", "create", "update"]

    def test_a_token_bound_to_another_resource_is_refused(self):
        user, app = _user(), _client()
        raw = _token(app, user, _profile())
        token = Token.objects.by_value(raw).get()
        token.set_resources(["https://elsewhere.example.com/mcp"])
        token.save()
        assert verify(raw) is None

    def test_a_token_bound_to_mcp_is_accepted(self):
        user, app = _user(), _client()
        raw = _token(app, user, _profile())
        token = Token.objects.by_value(raw).get()
        token.set_resources([mcp_resource()])
        token.save()
        assert verify(raw) is not None


class TestConnectionsList:
    def test_connections_show_their_profile(self, admin_api):
        profile = _profile(create=True)
        _token(_client(), _user(), profile)

        row = admin_api.get("/api/iam/connected-apps/all/").json()["results"][0]

        assert row["profile"]["name"] == "Read and create"
        assert row["profile"]["actions"] == ["read", "create"]

    def test_a_bad_user_filter_is_a_400(self, admin_api):
        response = admin_api.get("/api/iam/connected-apps/all/?user=not-a-uuid")
        assert response.status_code == 400
