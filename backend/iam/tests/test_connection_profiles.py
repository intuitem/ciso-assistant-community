import base64
import hashlib
import importlib
import secrets
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from allauth.idp.oidc.models import Client, Token
from django.apps import apps
from django.core.cache import cache
from django.utils import timezone
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.startup import startup
from iam.models import AppGrant, ConnectionProfile, User, UserGroup
from mcp_server.oauth import verify

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("mcp_on")]

AUTHORIZE_URL = "/api/identity/o/authorize"
PROFILES_URL = "/api/iam/connection-profiles/"
REDIRECT_URI = "http://localhost:9999/callback"


@pytest.fixture(autouse=True)
def _clean():
    cache.clear()
    # start from no profile: each test sets up the ones it needs
    ConnectionProfile.objects.all().delete()


def _profile(name="Read only", level="read", is_default=False):
    return ConnectionProfile.objects.create(
        name=name, level=level, is_default=is_default
    )


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
    client.set_scopes(["openid", "mcp:read", "mcp:write"])
    client.save()
    return client


def _token(client, user, profile=None, scopes=("mcp:read",)):
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
        AppGrant.objects.create(user=user, client=client, profile=profile)
    return raw


def _authorize(http, client, user, scope="openid mcp:read"):
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
        },
    )


def _consent(http, page, profile_id):
    signed = page.context["form"]["request"].value()
    return http.post(
        AUTHORIZE_URL,
        {"request": signed, "action": "grant", "profile": profile_id},
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
    def test_lists_profiles_lowest_first_with_the_default_checked(self, client):
        _profile("Full", "update")
        default = _profile("Read only", "read", is_default=True)

        page = _authorize(client, _client(), _user())

        assert page.status_code == 200
        items = page.context["profiles"]
        assert [item["profile"].name for item in items] == ["Read only", "Full"]
        assert [item["checked"] for item in items] == [True, False]
        assert "scopes" not in page.context["form"].fields
        assert str(default.pk) in page.content.decode()

    def test_the_chosen_profile_becomes_the_grant(self, client):
        _profile("Read only", "read", is_default=True)
        full = _profile("Full", "update")
        user, app = _user(), _client()

        response = _consent(client, _authorize(client, app, user), full.pk)

        assert _code(response)
        assert AppGrant.objects.get(user=user, client=app).profile == full

    def test_consenting_again_replaces_the_grant(self, client):
        read = _profile("Read only", "read", is_default=True)
        full = _profile("Full", "update")
        user, app = _user(), _client()
        _consent(client, _authorize(client, app, user), full.pk)

        _consent(client, _authorize(client, app, user), read.pk)

        assert AppGrant.objects.get(user=user, client=app).profile == read

    def test_a_tampered_profile_is_refused(self, client):
        _profile(is_default=True)
        user, app = _user(), _client()

        response = _consent(
            client,
            _authorize(client, app, user),
            "00000000-0000-0000-0000-000000000000",
        )

        assert not _code(response)
        assert not AppGrant.objects.exists()

    def test_skip_consent_uses_the_default(self, client):
        _profile("Full", "update")
        default = _profile("Read only", "read", is_default=True)
        user, app = _user(), _client(skip_consent=True)

        response = _authorize(client, app, user)

        assert _code(response)
        assert AppGrant.objects.get(user=user, client=app).profile == default

    def test_no_profile_at_all_is_refused(self, client):
        response = _authorize(client, _client(skip_consent=True), _user())

        assert response.status_code == 403
        assert b"has not set up what AI apps may do" in response.content

    def test_a_plain_sign_in_is_not_affected(self, client):
        response = _authorize(client, _client(skip_consent=True), _user(), "openid")

        assert _code(response)
        assert not AppGrant.objects.exists()


class TestBackendMcp:
    def test_a_token_without_grant_is_refused(self):
        _profile(is_default=True)
        assert verify(_token(_client(), _user())) is None

    def test_the_level_comes_from_the_profile(self):
        profile = _profile("Vendor helper", "create")
        access = verify(_token(_client(), _user(), profile))
        assert access.claims == {"level": "create", "profile": "Vendor helper"}

    def test_a_profile_change_applies_on_the_next_call(self):
        profile = _profile("Vendor helper", "create")
        raw = _token(_client(), _user(), profile)

        profile.level = "read"
        profile.save()

        assert verify(raw).claims["level"] == "read"

    def test_a_personal_access_token_keeps_full_rights(self):
        user = _user()
        raw = AuthToken.objects.create(user=user)[1]
        assert verify(raw).claims["level"] == "approve"


class TestDefault:
    def test_only_one_profile_is_the_default(self):
        first = _profile("A", is_default=True)
        second = _profile("B", is_default=True)
        first.refresh_from_db()
        assert not first.is_default
        assert ConnectionProfile.default() == second

    def test_without_a_marked_default_the_lowest_level_counts(self):
        _profile("Full", "update")
        read = _profile("Read", "read")
        assert ConnectionProfile.default() == read


class TestAdminApi:
    def test_lists_profiles_with_their_connection_count(self, admin_api):
        profile = _profile()
        _token(_client(), _user(), profile)

        rows = admin_api.get(PROFILES_URL).json()["results"]

        assert [(r["name"], r["connections"]) for r in rows] == [("Read only", 1)]

    def test_deleting_a_profile_revokes_only_its_connections(self, admin_api):
        doomed, kept = _profile("Doomed"), _profile("Kept")
        alice, bruno = _user("alice@example.com"), _user("bruno@example.com")
        app_x, app_y = _client(), _client()
        cut = _token(app_x, alice, doomed)
        _token(app_y, bruno, doomed)
        # alice on app_y uses another profile: it must survive
        survivor = _token(app_y, alice, kept)

        response = admin_api.delete(f"{PROFILES_URL}{doomed.pk}/")

        assert response.json() == {"revoked": 2}
        assert verify(cut) is None
        assert verify(survivor) is not None

    def test_is_for_admins_only(self):
        api = APIClient()
        api.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=_user())[1]}"
        )
        assert api.get(PROFILES_URL).status_code == 403

    def test_connections_show_their_profile(self, admin_api):
        profile = _profile("Vendor helper", "create")
        _token(_client(), _user(), profile)

        row = admin_api.get("/api/iam/connected-apps/all/").json()["results"][0]

        assert row["profile"]["name"] == "Vendor helper"


def test_migration_seeds_profiles_and_grants_existing_connections():
    migration = importlib.import_module("iam.migrations.0035_connection_profiles")
    reader, writer = _user("reader@example.com"), _user("writer@example.com")
    app = _client()
    _token(app, reader, scopes=("mcp:read",))
    _token(app, writer, scopes=("mcp:read", "mcp:write"))

    migration.seed_profiles_and_grants(apps, None)
    migration.seed_profiles_and_grants(apps, None)

    assert ConnectionProfile.objects.count() == 2
    assert ConnectionProfile.default().name == "Read only"
    assert AppGrant.objects.get(user=reader).profile.level == "read"
    assert AppGrant.objects.get(user=writer).profile.level == "update"
