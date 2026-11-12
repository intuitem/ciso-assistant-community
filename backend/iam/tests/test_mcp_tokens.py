import secrets
import uuid
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
import structlog
from allauth.idp.oidc.models import Client, Token
from auditlog.models import LogEntry
from django.apps import apps
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import Resolver404, resolve
from django.utils import timezone
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.context import mcp_access_var
from core.models import AppliedControl, Vulnerability
from core.permissions import IsGlobalAdmin, RBACPermissions
from core.startup import startup
from crq.models import QuantitativeRiskStudy
from global_settings.models import GlobalSettings
from global_settings.serializers import FeatureFlagsSerializer
from iam.delegation import ACTION_OF_PREFIX, CUSTOM_ACTIONS, allows
from iam.mcp_access import has_shared_cache
from iam.mcp_access import mcp_access_for
from iam.mcp_inventory import (
    OPERATIONS,
    READ,
    SERVER_OPERATIONS,
    effect,
    is_inventoried,
)
from iam.mcp_tokens import MCPTokenMiddleware
from iam.models import (
    AppGrant,
    ConnectionProfile,
    Folder,
    RoleAssignment,
    User,
    UserGroup,
)
from iam.oidc_adapter import mcp_resource
from iam.tests.mcp_tool_calls import ANY, calls_by_tool, tool_actions, tool_calls
from tprm.models import Entity, Representative
from webhooks.ocsf import log_entry_to_ocsf, log_entry_to_raw

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("mcp_on")]

MEMCACHED = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": "memcached:11211",
    }
}


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


@pytest.fixture
def admin():
    """A global administrator: RBAC allows everything, so whatever is refused
    below is refused by the MCP rules."""
    startup(sender=None)
    user = User.objects.create_superuser("admin@example.com")
    group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = group.folder
    user.can_connect_apps = True
    user.save()
    group.user_set.add(user)
    return user


def _client(name="Claude Code"):
    client = Client(name=name, type=Client.Type.PUBLIC, data={"dcr": True})
    client.set_redirect_uris(["http://localhost:9999/callback"])
    client.set_scopes(["openid", "mcp"])
    client.save()
    return client


def _mcp_token(user, *actions, resources=None, scopes=("mcp",)) -> str:
    client = _client()
    raw = secrets.token_urlsafe(32)
    token = Token(
        type=Token.Type.ACCESS_TOKEN,
        client=client,
        user=user,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    token.set_value(raw)
    token.set_scopes(list(scopes))
    token.set_resources([mcp_resource()] if resources is None else resources)
    token.save()
    profile = ConnectionProfile.matching(
        "create" in actions, "update" in actions, "delete" in actions
    )
    AppGrant.consent(user.pk, client.pk, profile)
    return raw


def _call(raw, method="get", path="/api/folders/", **kwargs):
    return getattr(APIClient(), method)(
        path, HTTP_AUTHORIZATION=f"Bearer {raw}", format="json", **kwargs
    )


def _new_control(name):
    return {"name": name, "folder": str(Folder.get_root_folder().id)}


class TestTokens:
    def test_a_bound_token_with_a_grant_is_accepted(self, admin):
        access = mcp_access_for(_mcp_token(admin))
        assert access.user == admin
        assert access.actions == ["read"]

    def test_an_unbound_token_is_accepted(self, admin):
        assert mcp_access_for(_mcp_token(admin, resources=[])) is not None

    def test_a_token_for_another_resource_is_refused(self, admin):
        raw = _mcp_token(admin, resources=["https://elsewhere.example/mcp"])
        assert mcp_access_for(raw) is None

    def test_a_token_without_the_mcp_scope_is_not_an_mcp_token(self, admin):
        assert mcp_access_for(_mcp_token(admin, scopes=("openid",))) is None

    def test_an_expired_token_is_refused(self, admin):
        raw = _mcp_token(admin)
        Token.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        assert mcp_access_for(raw) is None

    def test_a_user_who_may_no_longer_connect_apps_is_refused(self, admin):
        raw = _mcp_token(admin)
        User.objects.filter(pk=admin.pk).update(can_connect_apps=False)
        assert mcp_access_for(raw) is None

    def test_a_token_without_a_grant_is_refused(self, admin):
        raw = _mcp_token(admin)
        AppGrant.objects.all().delete()
        assert mcp_access_for(raw) is None

    def test_mcp_turned_off_refuses_every_token(self, admin):
        from global_settings.utils import clear_feature_flags_cache

        raw = _mcp_token(admin)
        flags = GlobalSettings.objects.get(name=GlobalSettings.Names.FEATURE_FLAGS)
        flags.value = {**flags.value, "mcp": False}
        flags.save()
        clear_feature_flags_cache()
        assert mcp_access_for(raw) is None

    def test_writes_wait_for_the_write_flag(self, admin, request):
        raw = _mcp_token(admin, "create", "update")
        assert mcp_access_for(raw).actions == ["read"]
        request.getfixturevalue("mcp_write_on")
        assert mcp_access_for(raw).actions == ["read", "create", "update"]

    def test_garbage_is_refused(self):
        assert mcp_access_for("not-a-token") is None


class TestSinglePort:
    def test_an_mcp_token_works_on_the_api(self, admin):
        response = _call(_mcp_token(admin))
        assert response.status_code == 200, response.content
        assert "results" in response.json()

    def test_a_refused_mcp_token_gets_401(self, admin):
        raw = _mcp_token(admin)
        AppGrant.objects.all().delete()
        assert _call(raw).status_code == 401

    def test_a_token_for_another_resource_gets_401(self, admin):
        raw = _mcp_token(admin, resources=["https://elsewhere.example/mcp"])
        assert _call(raw).status_code == 401

    def test_an_operation_outside_the_inventory_is_refused(self, admin):
        assert _call(_mcp_token(admin), path="/api/iam/auth-tokens/").status_code == 403

    def test_an_unknown_path_is_not_found(self, admin):
        assert _call(_mcp_token(admin), path="/api/nothing-here/").status_code == 404

    def test_a_get_that_writes_is_refused(self, admin, mcp_write_on):
        response = _call(
            _mcp_token(admin, "create", "update", "delete"),
            path=f"/api/loaded-libraries/{uuid.uuid4()}/update/",
        )
        assert response.status_code == 403

    def test_field_choices_of_a_collection_tools_read(self, admin):
        response = _call(_mcp_token(admin), path="/api/applied-controls/status/")
        assert response.status_code == 200

    def test_other_credentials_are_unaffected(self, admin):
        api = APIClient()
        api.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=admin)[1]}"
        )
        assert api.get("/api/iam/auth-tokens/").status_code == 200

    def test_the_profile_holds_in_the_backend(self, admin, mcp_write_on):
        path = "/api/applied-controls/"
        refused = _call(_mcp_token(admin), "post", path, data=_new_control("A"))
        allowed = _call(
            _mcp_token(admin, "create"), "post", path, data=_new_control("B")
        )
        assert refused.status_code == 403
        assert allowed.status_code == 201

    def test_the_write_flag_holds_in_the_backend(self, admin):
        response = _call(
            _mcp_token(admin, "create"),
            "post",
            "/api/applied-controls/",
            data=_new_control("A"),
        )
        assert response.status_code == 403

    def test_delete_needs_its_own_action(self, admin, mcp_write_on):
        doomed = Vulnerability.objects.create(
            name="Doomed", folder=Folder.get_root_folder()
        )
        path = f"/api/vulnerabilities/{doomed.id}/"
        assert (
            _call(_mcp_token(admin, "create", "update"), "delete", path).status_code
            == 403
        )
        assert _call(_mcp_token(admin, "delete"), "delete", path).status_code == 204

    def test_an_action_marked_update_needs_update(self, admin, mcp_write_on):
        # the view checks add_ but updates: it needs both actions
        study = QuantitativeRiskStudy.objects.create(
            name="Study", folder=Folder.get_root_folder()
        )
        path = (
            f"/api/crq/quantitative-risk-studies/{study.id}/retrigger-all-simulations/"
        )
        for actions in (("create",), ("update",)):
            assert _call(_mcp_token(admin, *actions), "post", path).status_code == 403
        allowed = _call(_mcp_token(admin, "create", "update"), "post", path)
        assert allowed.status_code == 200

    def test_an_app_cannot_create_a_user_account(self, admin, mcp_write_on):
        entity = Entity.objects.create(name="Acme", folder=Folder.get_root_folder())
        raw = _mcp_token(admin, "create")
        payload = {"entity": str(entity.id), "email": "rep@acme.example"}

        refused = _call(
            raw,
            "post",
            "/api/representatives/",
            data={**payload, "create_user": True},
        )
        allowed = _call(raw, "post", "/api/representatives/", data=payload)

        assert refused.status_code == 400
        assert not User.objects.filter(email="rep@acme.example").exists()
        assert allowed.status_code == 201, allowed.content
        assert Representative.objects.get(email="rep@acme.example").user is None

    def test_changes_made_through_an_app_name_it(self, admin, mcp_write_on):
        _call(
            _mcp_token(admin, "create"),
            "post",
            "/api/applied-controls/",
            data=_new_control("Tagged"),
        )
        control = AppliedControl.objects.get(name="Tagged")
        entry = LogEntry.objects.get_for_object(control).latest("timestamp")
        via = entry.additional_data["via_app"]
        assert via["name"] == "Claude Code"
        assert via["profile"] == "Read and create"
        entry.actor_email = admin.email
        assert log_entry_to_ocsf(entry)["actor"]["app_name"] == "Claude Code"
        assert log_entry_to_raw(entry)["via_app"] == via

    def test_the_next_request_does_not_keep_the_app(self, admin):
        _call(_mcp_token(admin))
        api = APIClient()
        api.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=admin)[1]}"
        )
        api.post("/api/applied-controls/", _new_control("By hand"), format="json")
        control = AppliedControl.objects.get(name="By hand")
        entry = LogEntry.objects.get_for_object(control).latest("timestamp")
        assert "via_app" not in (entry.additional_data or {})

    def test_the_request_log_names_the_app(self, admin):
        seen = {}

        def view(request):
            seen.update(structlog.contextvars.get_contextvars())
            return HttpResponse()

        raw = _mcp_token(admin)
        request = RequestFactory().get(
            "/api/folders/", HTTP_AUTHORIZATION=f"Bearer {raw}"
        )
        structlog.contextvars.clear_contextvars()
        try:
            MCPTokenMiddleware(view)(request)
        finally:
            structlog.contextvars.clear_contextvars()
        assert seen["mcp_app"] == Client.objects.get().id

    def test_the_request_log_names_the_app_of_a_refused_request(self, admin):
        raw = _mcp_token(admin)
        # not an operation the tools use: refused before any view runs
        request = RequestFactory().delete(
            "/api/folders/", HTTP_AUTHORIZATION=f"Bearer {raw}"
        )
        structlog.contextvars.clear_contextvars()
        try:
            response = MCPTokenMiddleware(lambda request: HttpResponse())(request)
            seen = structlog.contextvars.get_contextvars()
        finally:
            structlog.contextvars.clear_contextvars()
        assert response.status_code == 403
        assert seen["mcp_app"] == Client.objects.get().id


class TestAccessLookup:
    PATH = "/api/iam/mcp/access/"

    def test_the_mcp_server_learns_the_connection(self, admin, mcp_write_on):
        response = _call(_mcp_token(admin, "create"), path=self.PATH)
        assert response.status_code == 200
        assert response.json() == {
            "user": str(admin.pk),
            "client_id": Client.objects.get().id,
            "actions": ["read", "create"],
            "profile": "Read and create",
            "app": "Claude Code",
        }

    def test_it_says_read_only_while_writes_are_off(self, admin):
        response = _call(_mcp_token(admin, "create"), path=self.PATH)
        assert response.json()["actions"] == ["read"]

    def test_a_personal_access_token_learns_nothing(self, admin):
        api = APIClient()
        api.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=admin)[1]}"
        )
        assert api.get(self.PATH).status_code == 403

    def test_a_token_without_a_grant_learns_nothing(self, admin):
        raw = _mcp_token(admin)
        AppGrant.objects.all().delete()
        assert _call(raw, path=self.PATH).status_code == 401


class TestBackstop:
    """With an MCP token, administration and credentials are refused whatever
    the user's role, and data follows the connection's actions."""

    def _allowed(self, user, codename, *actions):
        access = SimpleNamespace(actions=["read", *actions])
        token = mcp_access_var.set(access)
        try:
            return RoleAssignment.is_access_allowed(
                user,
                Permission.objects.get(codename=codename),
                Folder.get_root_folder(),
            )
        finally:
            mcp_access_var.reset(token)

    def test_data_follows_the_actions(self, admin):
        assert self._allowed(admin, "view_appliedcontrol")
        assert not self._allowed(admin, "add_appliedcontrol")
        assert self._allowed(admin, "add_appliedcontrol", "create")
        assert not self._allowed(admin, "delete_appliedcontrol", "create", "update")
        assert self._allowed(admin, "delete_appliedcontrol", "delete")

    @pytest.mark.parametrize(
        "codename",
        ["add_user", "change_user", "add_folder", "change_role", "add_roleassignment"],
    )
    def test_administration_is_refused(self, admin, codename):
        assert not self._allowed(admin, codename, "create", "update", "delete")

    def test_reading_users_and_domains_is_allowed(self, admin):
        assert self._allowed(admin, "view_user")
        assert self._allowed(admin, "view_folder")

    @pytest.mark.parametrize(
        "codename",
        ["view_personalaccesstoken", "add_personalaccesstoken", "view_ssosettings"],
    )
    def test_credentials_and_secrets_are_refused(self, admin, codename):
        assert not self._allowed(admin, codename, "create", "update", "delete")

    def test_custom_permissions_are_refused(self, admin):
        custom = (
            Permission.objects.exclude(codename__regex=r"^(view|add|change|delete)_")
            .values_list("codename", flat=True)
            .first()
        )
        assert custom is not None
        assert not self._allowed(admin, custom, "create", "update", "delete")

    def test_a_custom_permission_passes_only_when_mapped(self):
        everything = SimpleNamespace(actions=["read", "create", "update", "delete"])
        # named like a read, but not mapped: refused
        assert not allows("view_user_full", everything)
        assert not allows("view_central_auditlog", everything)
        # mapped to read: follows the connection's actions
        assert allows("view_compliance_assessment_full", everything)
        nothing = SimpleNamespace(actions=[])
        assert not allows("view_compliance_assessment_full", nothing)

    def test_no_custom_permission_passes_by_its_name(self):
        """A new custom permission is refused until CUSTOM_ACTIONS maps it,
        even when it is named like a model permission."""
        everything = SimpleNamespace(actions=["read", "create", "update", "delete"])
        declared = {
            codename
            for model in apps.get_models()
            for codename, _ in model._meta.permissions
        }
        passing = {codename for codename in declared if allows(codename, everything)}
        assert passing == set(CUSTOM_ACTIONS)

    def test_the_admin_endpoints_are_refused(self, admin):
        request = SimpleNamespace(user=admin)
        token = mcp_access_var.set(SimpleNamespace(actions=["read"]))
        try:
            assert not IsGlobalAdmin().has_permission(request, None)
        finally:
            mcp_access_var.reset(token)
        assert IsGlobalAdmin().has_permission(request, None)


class TestSharedCache:
    @pytest.fixture(autouse=True)
    def _real_check(self, mcp_on, monkeypatch):
        # mcp_on stands in a shared cache; these tests check the real answer
        monkeypatch.setattr("iam.mcp_access.has_shared_cache", has_shared_cache)

    def _valid(self, **flags):
        row, _ = GlobalSettings.objects.get_or_create(
            name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {}}
        )
        return FeatureFlagsSerializer(row, data=flags, partial=True).is_valid()

    @pytest.mark.parametrize("flag", ["mcp", "mcp_write"])
    def test_mcp_needs_a_shared_cache(self, flag):
        assert not self._valid(**{flag: True})

    @pytest.mark.parametrize("flag", ["mcp", "mcp_write"])
    def test_mcp_can_be_turned_on_with_memcached(self, settings, flag):
        settings.CACHES = MEMCACHED
        assert self._valid(**{flag: True})

    def test_other_flags_do_not_need_it(self):
        assert self._valid(mcp=False, incidents=True)


def _checked_action(method, match) -> str | None:
    """The action of the permission RBACPermissions checks for this call: the
    one of its method, unless the view overrides it for this action."""
    codename = RBACPermissions.perms_map[method][0].split(".")[1]
    view_action = getattr(match.func, "actions", {}).get(method.lower())
    cls = getattr(match.func, "cls", None)
    overrides = getattr(cls, "permission_overrides", {})
    if isinstance(overrides, property):
        # some views choose their overrides from the request's method
        view = cls()
        view.request = SimpleNamespace(method=method)
        overrides = view.permission_overrides
    codename = overrides.get(view_action, codename)
    return ACTION_OF_PREFIX.get(codename.partition("_")[0])


class TestInventory:
    def test_it_covers_every_call_the_tools_make(self):
        missing = []
        for method, path in sorted(tool_calls()):
            match = resolve("/api" + path.replace(ANY, str(uuid.uuid4())))
            if not is_inventoried(method, match):
                missing.append((method, path, match.url_name))
        assert not missing, "add these to iam/mcp_inventory.py"

    def test_it_lists_nothing_the_tools_do_not_call(self):
        used = set(SERVER_OPERATIONS)
        for method, path in tool_calls():
            try:
                match = resolve("/api" + path.replace(ANY, str(uuid.uuid4())))
            except Resolver404:
                continue
            used.add((method, match.url_name))
        assert set(OPERATIONS) - used == set()

    def test_a_tool_is_refused_nothing_its_actions_cover(self):
        """A connection that holds a tool's actions is refused none of the
        tool's calls, so the MCP server and the backend cannot disagree. A call
        needs the effect the inventory marks and the action of the permission
        its view checks."""
        needed = tool_actions()
        refused = []
        for tool, calls in sorted(calls_by_tool().items()):
            held = needed[tool] | {READ}
            for method, path in sorted(calls):
                match = resolve("/api" + path.replace(ANY, str(uuid.uuid4())))
                required = {effect(method, match), _checked_action(method, match)}
                if not required <= held:
                    refused.append((tool, method, path, required - held))
        assert not refused, "declare these actions in ca_mcp (ALSO_NEEDS)"

    def test_every_write_tool_has_its_write_call(self):
        # the test above proves nothing for a tool whose calls are not found
        calls = calls_by_tool()
        silent = [
            tool
            for tool, actions in tool_actions().items()
            if tool in calls
            and actions != {READ}
            and all(method == "GET" for method, _ in calls[tool])
        ]
        assert not silent


def test_authorization_server_metadata_at_the_rfc8414_address(client):
    response = client.get("/.well-known/oauth-authorization-server/api")
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "*"
    assert response.json()["issuer"].endswith("/api")


@pytest.mark.parametrize(
    "path",
    [
        "/.well-known/oauth-authorization-server/api",
        "/api/.well-known/openid-configuration",
    ],
)
@pytest.mark.parametrize("host", ["localhost", "internal-proxy-name:8080"])
def test_metadata_endpoints_follow_the_public_url_not_the_host(
    client, settings, path, host
):
    # a proxy may send Host without the public port (nginx's $host does)
    settings.CISO_ASSISTANT_URL = "https://grc.example.com:8443"
    settings.ALLOWED_HOSTS = ["*"]
    metadata = client.get(path, HTTP_HOST=host).json()
    urls = {k: v for k, v in metadata.items() if k.endswith(("_endpoint", "_uri"))}
    assert metadata["issuer"] == "https://grc.example.com:8443/api"
    public = [urlsplit(v) for v in urls.values()]
    assert urls and all(
        (url.scheme, url.netloc) == ("https", "grc.example.com:8443") for url in public
    ), urls


def test_metadata_never_shows_the_default_port(client, settings):
    # clients drop :443, and the issuer must match what they fetched exactly
    settings.CISO_ASSISTANT_URL = "https://grc.example.com:443"
    metadata = client.get("/.well-known/oauth-authorization-server/api").json()
    assert metadata["issuer"] == "https://grc.example.com/api"
    urls = [v for k, v in metadata.items() if k.endswith(("_endpoint", "_uri"))]
    assert urls and all(urlsplit(v).netloc == "grc.example.com" for v in urls), urls
