import json
from urllib.parse import parse_qs, urlsplit

import pytest
import yaml

from automation.workflows.engine import DISPLAY_MAX_ITEMS, start_instance
from automation.workflows.import_export import import_workflow
from automation.workflows.models import WorkflowInstance, WorkflowToken
from automation.workflows.serializers import WorkflowInstanceReadSerializer
from automation.workflows.tasks import retry_token_task
from automation.workflows.tests.helpers import publisher_user
from automation.workflows.tests.test_landing_zones import make_metric
from automation.workflows.tests.test_shipped_libraries import LIBRARY_DIR
from automation.workflows.tests.test_unreachable_tool import make_domain
from core.models import Asset
from metrology.models import CustomMetricSample

GRAPH_SCOPE = "https://graph.microsoft.com/.default"
DEFENDER_SCOPE = "https://api.securitycenter.microsoft.com/.default"
GLOBAL_ADMIN = "62e90394-69f5-4237-9190-012177145e10"
S1_HOST = "tenant.sentinelone.net"


class Response:
    def __init__(self, payload, status=200, raw=False):
        self.status_code = status
        self.payload = payload
        self.text = payload if raw else json.dumps(payload)

    def json(self):
        if isinstance(self.payload, str):
            return json.loads(self.payload)
        return self.payload


class Vendors:
    def __init__(self, devices=0, users_without_mfa=0, graph_page=2):
        self.devices = [
            {
                "id": f"m{i:05d}",
                "computerDnsName": f"host-{i:05d}.corp.local",
                "osPlatform": "Windows11",
                "version": "23H2",
                "exposureLevel": "Medium",
                "riskScore": "Low",
                "lastSeen": "2026-10-08T03:00:00Z",
            }
            for i in range(devices)
        ]
        self.users = [
            {"id": f"u{i}", "userPrincipalName": f"person{i}@contoso.com"}
            for i in range(users_without_mfa)
        ]
        self.graph_page = graph_page
        self.throttle = set()
        self.calls = []
        self.rejected = []

    def reject(self, reason):
        self.rejected.append(reason)
        return Response({"error": {"code": "BadRequest", "message": reason}}, 400)

    def post(self, url, data=None, **kwargs):
        parts = urlsplit(url)
        self.calls.append(("POST", url))
        if parts.hostname != "login.microsoftonline.com" or not parts.path.endswith(
            "/oauth2/v2.0/token"
        ):
            raise AssertionError(f"unexpected token endpoint {url}")
        if set(data) != {"grant_type", "client_id", "client_secret", "scope"}:
            return self.reject(f"token form fields {sorted(data)}")
        if data["grant_type"] != "client_credentials" or data["client_secret"] != "ms":
            return Response({"error": "invalid_client"}, 401)
        if data["scope"] not in (GRAPH_SCOPE, DEFENDER_SCOPE):
            return self.reject(f"scope {data['scope']}")
        return Response({"access_token": f"token:{data['scope']}", "expires_in": 3599})

    def request(self, method, url, headers=None, **kwargs):
        parts = urlsplit(url)
        query = {key: values[0] for key, values in parse_qs(parts.query).items()}
        headers = headers or {}
        self.calls.append((method, url))
        if parts.hostname == "graph.microsoft.com":
            return self.graph(parts.path, query, headers)
        if parts.hostname == "api.security.microsoft.com":
            return self.defender(parts.path, query, headers)
        if parts.hostname == S1_HOST:
            return self.sentinelone(parts.path, query, headers)
        raise AssertionError(f"unexpected host {parts.hostname}")

    def allowed(self, query, names):
        unknown = set(query) - set(names)
        return f"unsupported query parameters {sorted(unknown)}" if unknown else None

    def graph(self, path, query, headers):
        if headers.get("Authorization") != f"Bearer token:{GRAPH_SCOPE}":
            return Response({"error": {"code": "InvalidAuthenticationToken"}}, 401)
        if path == "/v1.0/reports/authenticationMethods/userRegistrationDetails":
            problem = self.allowed(query, {"$filter", "$skiptoken"})
            if problem:
                return self.reject(problem)
            if query.get("$filter") != "isMfaRegistered eq false":
                return self.reject(f"filter {query.get('$filter')}")
            start = int(query.get("$skiptoken", 0))
            page = {"value": self.users[start : start + self.graph_page]}
            if start + self.graph_page < len(self.users):
                page["@odata.nextLink"] = (
                    "https://graph.microsoft.com/v1.0/reports/authenticationMethods/"
                    "userRegistrationDetails?$filter=isMfaRegistered%20eq%20false"
                    f"&$skiptoken={start + self.graph_page}"
                )
            return Response(page)
        if path == "/v1.0/roleManagement/directory/roleAssignments":
            problem = self.allowed(query, {"$filter"})
            if problem:
                return self.reject(problem)
            if query.get("$filter") != f"roleDefinitionId eq '{GLOBAL_ADMIN}'":
                return self.reject(f"filter {query.get('$filter')}")
            return Response({"value": [{"id": f"a{i}"} for i in range(3)]})
        if path == "/v1.0/users/$count":
            if headers.get("ConsistencyLevel") != "eventual":
                return self.reject("$count needs ConsistencyLevel: eventual")
            problem = self.allowed(query, {"$filter"})
            if problem:
                return self.reject(problem)
            if query.get("$filter") != "userType eq 'Guest'":
                return self.reject(f"filter {query.get('$filter')}")
            return Response("12", raw=True)
        return Response({"error": {"code": "Request_ResourceNotFound"}}, 404)

    def defender(self, path, query, headers):
        if headers.get("Authorization") != f"Bearer token:{DEFENDER_SCOPE}":
            return Response({"error": {"code": "Forbidden"}}, 403)
        if path != "/api/machines":
            return Response({"error": {"code": "NotFound"}}, 404)
        if "machines" in self.throttle:
            self.throttle.discard("machines")
            return Response({"error": {"code": "TooManyRequests"}}, 429)
        problem = self.allowed(query, {"$filter", "$top", "$skip"})
        if problem:
            return self.reject(problem)
        if query.get("$filter") != "healthStatus eq 'Active'":
            return self.reject(f"filter {query.get('$filter')}")
        top = int(query.get("$top", 10000))
        if not 1 <= top <= 10000:
            return self.reject(f"$top {top}")
        skip = int(query.get("$skip", 0))
        return Response({"value": self.devices[skip : skip + top]})

    def sentinelone(self, path, query, headers):
        if headers.get("Authorization") != "ApiToken s1":
            return Response({"errors": [{"title": "Unauthorized"}]}, 401)
        if path == "/web/api/v2.1/agents":
            problem = self.allowed(query, {"limit", "isUpToDate", "cursor"})
            total = 17 if query.get("isUpToDate") == "false" else 250
        elif path == "/web/api/v2.1/threats":
            problem = self.allowed(query, {"limit", "incidentStatuses", "cursor"})
            statuses = set((query.get("incidentStatuses") or "").split(","))
            if not statuses <= {"unresolved", "in_progress", "resolved"}:
                problem = f"incidentStatuses {sorted(statuses)}"
            total = 4
        else:
            return Response({"errors": [{"title": "Not found"}]}, 404)
        if problem:
            return self.reject(problem)
        if not 1 <= int(query.get("limit", 10)) <= 1000:
            return self.reject("limit out of range")
        return Response(
            {"data": [{}], "pagination": {"totalItems": total, "nextCursor": "next"}}
        )


@pytest.fixture
def vendors(monkeypatch):
    monkeypatch.setattr(
        "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
    )
    holder = Vendors()

    def install(**kwargs):
        fresh = Vendors(**kwargs)
        holder.__dict__.update(fresh.__dict__)
        return holder

    monkeypatch.setattr("requests.request", lambda *a, **k: holder.request(*a, **k))
    monkeypatch.setattr("requests.post", lambda *a, **k: holder.post(*a, **k))
    return install


def install_recipe(stem, domain, variables, secrets):
    path = LIBRARY_DIR / f"{stem}.yaml"
    entry = yaml.safe_load(path.read_text())["objects"]["workflows"][0]
    for variable in entry["graph"]["variables"]:
        if variable["key"] in variables:
            variable["default_value"] = variables[variable["key"]]
    workflow, _ = import_workflow(entry, domain, user=publisher_user(), secrets=secrets)
    version = workflow.draft_version
    version.run_as = publisher_user()
    version.save()
    return version


def readings(*metrics):
    return [
        CustomMetricSample.objects.get(metric_instance=metric).value["result"]
        for metric in metrics
    ]


@pytest.mark.django_db
class TestEntraRecipe:
    def test_counts_land_as_metric_samples(self, vendors):
        vendor = vendors(users_without_mfa=5)
        domain = make_domain("Entra")
        no_mfa, admins, guests = (make_metric(domain) for _ in range(3))
        version = install_recipe(
            "workflow-operations-entra-identity-metrics",
            domain,
            {
                "tenant_id": "contoso",
                "client_id": "app",
                "metric_no_mfa": str(no_mfa.id),
                "metric_global_admins": str(admins.id),
                "metric_guests": str(guests.id),
            },
            {"entra_client_secret": "ms"},
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert vendor.rejected == []
        assert readings(no_mfa, admins, guests) == [5, 3, 12]
        assert "person0@contoso.com" not in json.dumps(instance.node_outputs)
        assert sum(1 for method, _ in vendor.calls if method == "POST") == 3


@pytest.mark.django_db
class TestDefenderRecipe:
    def install(self, domain):
        return install_recipe(
            "workflow-operations-defender-device-inventory",
            domain,
            {"tenant_id": "contoso", "client_id": "app"},
            {"defender_client_secret": "ms"},
        )

    def test_pages_by_offset_and_keeps_one_asset_per_device(self, vendors):
        vendor = vendors(devices=2500)
        domain = make_domain("Defender")
        version = self.install(domain)
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert vendor.rejected == []
        pages = [parse_qs(urlsplit(url).query) for method, url in vendor.calls[1:]]
        assert [page["$top"] for page in pages] == [["1000"]] * 3
        assert [page.get("$skip") for page in pages] == [None, ["1000"], ["2000"]]
        assert instance.node_outputs["keep_assets"]["created"] == 2500
        assert instance.node_outputs["list_devices"]["truncated"] is False
        assert Asset.objects.filter(folder=domain).count() == 2500

        again = start_instance(version)
        assert again.node_outputs["keep_assets"]["updated"] == 2500
        assert Asset.objects.filter(folder=domain).count() == 2500

    def test_an_inventory_past_the_output_limit_says_so(self, vendors, settings):
        settings.WORKFLOW_NODE_OUTPUT_MAX_ITEMS = 2000
        vendors(devices=2500)
        domain = make_domain("Large")
        instance = start_instance(self.install(domain))
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.node_outputs["list_devices"]["truncated"] is True
        kept = instance.node_outputs["keep_assets"]
        assert (kept["received"], kept["created"], kept["failed"]) == (2000, 2000, 0)

    def test_throttling_is_retried(self, vendors):
        vendor = vendors(devices=3)
        vendor.throttle.add("machines")
        domain = make_domain("Throttled")
        instance = start_instance(self.install(domain))
        token = instance.tokens.get(status=WorkflowToken.Status.RETRYING)
        assert token.retry_count == 1
        retry_token_task.call_local(str(token.id))
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert Asset.objects.filter(folder=domain).count() == 3


@pytest.mark.django_db
class TestSentinelOneRecipe:
    def test_counts_land_as_metric_samples(self, vendors):
        vendor = vendors()
        domain = make_domain("S1")
        agents, outdated, threats = (make_metric(domain) for _ in range(3))
        instance = start_instance(
            install_recipe(
                "workflow-operations-sentinelone-coverage",
                domain,
                {
                    "console_url": f"https://{S1_HOST}",
                    "metric_agents": str(agents.id),
                    "metric_outdated_agents": str(outdated.id),
                    "metric_open_threats": str(threats.id),
                },
                {"s1_api_token": "s1"},
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert vendor.rejected == []
        assert readings(agents, outdated, threats) == [250, 17, 4]


class TestTheFakeIsStrict:
    def test_graph_count_without_consistency_level_is_refused(self):
        vendor = Vendors()
        response = vendor.graph(
            "/v1.0/users/$count",
            {"$filter": "userType eq 'Guest'"},
            {"Authorization": f"Bearer token:{GRAPH_SCOPE}"},
        )
        assert response.status_code == 400

    def test_registration_report_refuses_count(self):
        vendor = Vendors()
        response = vendor.graph(
            "/v1.0/reports/authenticationMethods/userRegistrationDetails",
            {"$filter": "isMfaRegistered eq false", "$count": "true"},
            {"Authorization": f"Bearer token:{GRAPH_SCOPE}"},
        )
        assert response.status_code == 400

    def test_defender_refuses_a_graph_token(self):
        vendor = Vendors()
        response = vendor.defender(
            "/api/machines", {}, {"Authorization": f"Bearer token:{GRAPH_SCOPE}"}
        )
        assert response.status_code == 403

    def test_sentinelone_refuses_unknown_statuses(self):
        vendor = Vendors()
        response = vendor.sentinelone(
            "/web/api/v2.1/threats",
            {"incidentStatuses": "open", "limit": "1"},
            {"Authorization": "ApiToken s1"},
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestCanvasGetsAPreview:
    def test_large_outputs_are_trimmed_for_the_api_only(self, vendors):
        vendors(devices=1200)
        domain = make_domain("Preview")
        instance = start_instance(
            install_recipe(
                "workflow-operations-defender-device-inventory",
                domain,
                {"tenant_id": "contoso", "client_id": "app"},
                {"defender_client_secret": "ms"},
            )
        )
        instance.refresh_from_db()
        assert len(instance.node_outputs["list_devices"]["items"]) == 1200
        shown = WorkflowInstanceReadSerializer(instance).data["node_outputs"]
        items = shown["list_devices"]["items"]
        assert len(items) == DISPLAY_MAX_ITEMS + 1
        assert items[-1] == f"<{1200 - DISPLAY_MAX_ITEMS} more items>"
        assert shown["keep_assets"]["created"] == 1200
