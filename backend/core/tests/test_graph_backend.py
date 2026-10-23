"""Microsoft Graph transport: environment variables, the token step as the
failover point, the sendMail request, the one retry on an expired token, and
the errors reported in our words."""

import json
import re
from urllib.parse import parse_qs

import httpx
import pytest
from django.core import mail
from django.core.mail import EmailMessage

from ciso_assistant.mailers import build_mailers, describe
from core import graph_backend, mail_oauth2, mailer
from core.graph_backend import GraphError

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"

GRAPH_ENV = {
    "EMAIL_TRANSPORT": "graph",
    "EMAIL_GRAPH_TENANT_ID": "contoso.onmicrosoft.com",
    "EMAIL_HOST_USER": "noreply@example.com",
    "EMAIL_OAUTH2_CLIENT_ID": "client-1",
    "EMAIL_OAUTH2_CLIENT_SECRET": "s3cret",
}

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fresh_token_cache():
    mail_oauth2.clear_cache()
    yield
    mail_oauth2.clear_cache()


class FakeGraph:
    """Microsoft's two endpoints behind one httpx mock transport."""

    def __init__(self):
        self.token_requests = []
        self.sends = []
        self.expired_tokens = set()
        self.token_status = 200
        self.send_status = 202

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "login.microsoftonline.com":
            self.token_requests.append(
                (str(request.url), parse_qs(request.content.decode()))
            )
            if self.token_status != 200:
                return httpx.Response(
                    self.token_status,
                    json={"error": "invalid_client", "error_description": "bad secret"},
                )
            return httpx.Response(
                200,
                json={
                    "access_token": f"tok-{len(self.token_requests)}",
                    "expires_in": 3600,
                },
            )
        token = request.headers["Authorization"].removeprefix("Bearer ")
        self.sends.append((str(request.url), token, json.loads(request.content)))
        if token in self.expired_tokens:
            return httpx.Response(
                401,
                json={
                    "error": {
                        "code": "InvalidAuthenticationToken",
                        "message": "Access token has expired.",
                    }
                },
            )
        if self.send_status != 202:
            return httpx.Response(
                self.send_status,
                json={
                    "error": {
                        "code": "ErrorAccessDenied",
                        "message": "Access is denied. Check credentials and try again.\nMore lines.",
                    }
                },
            )
        return httpx.Response(202)


@pytest.fixture
def graph(monkeypatch):
    fake = FakeGraph()
    transport = httpx.MockTransport(fake.handler)
    monkeypatch.setattr(graph_backend, "TRANSPORT", transport)
    monkeypatch.setattr(mail_oauth2, "TRANSPORT", transport)
    return fake


def configure(settings, env=GRAPH_ENV, rescue=None):
    mailers = build_mailers(env)
    if rescue:
        mailers["rescue"] = {"BACKEND": rescue}
    settings.MAILERS = mailers
    settings.DEFAULT_FROM_EMAIL = "noreply@example.com"


# --- environment ---------------------------------------------------------------


def test_graph_values_build_a_graph_mailer():
    entry = build_mailers(GRAPH_ENV)["default"]
    assert entry["BACKEND"] == "core.graph_backend.EmailBackend"
    options = entry["OPTIONS"]
    assert options["mailbox"] == "noreply@example.com"
    assert "host" not in options
    oauth2 = options["oauth2"]
    assert oauth2["grant_type"] == "client_credentials"
    assert oauth2["token_url"] == (
        "https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/v2.0/token"
    )
    assert oauth2["scope"] == "https://graph.microsoft.com/.default"
    assert (oauth2["client_id"], oauth2["client_secret"]) == ("client-1", "s3cret")


def test_startup_log_redacts_the_client_secret():
    lines = describe(build_mailers(GRAPH_ENV))
    assert len(lines) == 1
    assert "s3cret" not in lines[0]
    assert "'client_secret': '***'" in lines[0]
    assert "'client_id': 'client-1'" in lines[0]


@pytest.mark.parametrize(
    "missing, expected",
    [
        ("EMAIL_GRAPH_TENANT_ID", "EMAIL_GRAPH_TENANT_ID is required"),
        ("EMAIL_HOST_USER", "EMAIL_HOST_USER (the mailbox to send as) is required"),
        ("EMAIL_OAUTH2_CLIENT_SECRET", "EMAIL_OAUTH2_CLIENT_SECRET required"),
    ],
)
def test_missing_graph_variables_stop_startup(missing, expected):
    env = {key: value for key, value in GRAPH_ENV.items() if key != missing}
    with pytest.raises(ValueError, match=re.escape(expected)):
        build_mailers(env)


@pytest.mark.parametrize(
    "tenant",
    [
        "evil.example/../x",
        "common",
        "organizations",
        "consumers",
        "contoso.onmicrosoft.com\n",
        "-bad.example",
        "x" * 254,
    ],
)
def test_tenant_must_be_a_guid_or_a_domain(tenant):
    with pytest.raises(ValueError, match="tenant GUID or domain name"):
        build_mailers({**GRAPH_ENV, "EMAIL_GRAPH_TENANT_ID": tenant})


@pytest.mark.parametrize(
    "tenant", ["31537af4-6d77-4bb9-a681-d2394888ea26", "contoso.onmicrosoft.com"]
)
def test_tenant_guid_or_domain_is_accepted(tenant):
    oauth2 = build_mailers({**GRAPH_ENV, "EMAIL_GRAPH_TENANT_ID": tenant})["default"][
        "OPTIONS"
    ]["oauth2"]
    assert oauth2["token_url"] == (
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    )


def test_graph_rescue_behind_an_smtp_primary():
    env = {"EMAIL_HOST": "smtp.example.com"}
    env.update({f"{key}_RESCUE": value for key, value in GRAPH_ENV.items()})
    mailers = build_mailers(env)
    assert mailers["default"]["BACKEND"] == "core.email_backend.EmailBackend"
    assert mailers["rescue"]["BACKEND"] == "core.graph_backend.EmailBackend"
    assert mailers["rescue"]["OPTIONS"]["oauth2"]["token_url"] == (
        "https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/v2.0/token"
    )


# --- sending -------------------------------------------------------------------


def test_send_posts_to_the_mailbox_with_a_bearer_token(settings, graph):
    configure(settings)
    mailer.send("Subject", "Body", "a@tests.local")
    ((token_url, form),) = graph.token_requests
    assert token_url == (
        "https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/v2.0/token"
    )
    assert form["grant_type"] == ["client_credentials"]
    assert form["scope"] == ["https://graph.microsoft.com/.default"]
    ((url, token, payload),) = graph.sends
    assert url == "https://graph.microsoft.com/v1.0/users/noreply@example.com/sendMail"
    assert token == "tok-1"
    assert payload == {
        "message": {
            "subject": "Subject",
            "body": {"contentType": "Text", "content": "Body"},
            "toRecipients": [{"emailAddress": {"address": "a@tests.local"}}],
        },
        "saveToSentItems": False,
    }


def test_html_body_and_a_different_sender(settings, graph):
    configure(settings)
    mailer.send(
        "S",
        "plain",
        "a@tests.local",
        html_body="<p>hi</p>",
        from_email="Help <hello@example.com>",
    )
    message = graph.sends[0][2]["message"]
    assert message["body"] == {"contentType": "HTML", "content": "<p>hi</p>"}
    assert message["from"] == {
        "emailAddress": {"address": "hello@example.com", "name": "Help"}
    }


def test_expired_token_is_retried_once_with_a_fresh_one(settings, graph):
    configure(settings)
    graph.expired_tokens = {"tok-1"}
    mailer.send("S", "b", "a@tests.local")
    assert [token for _, token, _ in graph.sends] == ["tok-1", "tok-2"]
    assert len(graph.token_requests) == 2


def test_rejected_send_is_final_and_reported_in_graphs_words(settings, graph):
    configure(settings, rescue=LOCMEM)
    graph.send_status = 403
    with pytest.raises(GraphError) as info:
        mailer.send("S", "b", "a@tests.local")
    assert mailer.describe_error(info.value) == (
        "Graph replied 403 ErrorAccessDenied: Access is denied. Check credentials and try again."
    )
    # Handed over, so no failover to the rescue mailer.
    assert mail.outbox == []


def test_token_failure_fails_over_to_the_rescue_mailer(settings, graph):
    configure(settings, rescue=LOCMEM)
    graph.token_status = 401
    mailer.send("S", "b", "a@tests.local")
    assert graph.sends == []
    assert [m.to for m in mail.outbox] == [["a@tests.local"]]


def test_attachments_are_refused_before_anything_is_sent(settings, graph):
    configure(settings)
    message = EmailMessage("S", "b", "noreply@example.com", ["a@tests.local"])
    message.attach("report.txt", b"data", "text/plain")
    with mailer.open_connection() as backend:
        with pytest.raises(ValueError, match="does not send attachments"):
            backend.send_messages([message])
    assert graph.sends == []


def test_send_test_reports_the_graph_mailer(settings, graph):
    configure(settings)
    result = mailer.send_test("admin@tests.local")
    assert result.ok is True
    assert result.mailer == "default"
    assert result.backend == "EmailBackend"
    assert graph.sends[0][2]["message"]["toRecipients"] == [
        {"emailAddress": {"address": "admin@tests.local"}}
    ]


def test_http_errors_are_described_in_our_words():
    request = httpx.Request("POST", "https://graph.microsoft.com/")
    assert mailer.describe_error(httpx.ProxyError("407", request=request)) == (
        "the HTTP proxy refused the connection"
    )
    assert mailer.describe_error(httpx.ConnectTimeout("t", request=request)) == (
        "connection timed out"
    )
    assert mailer.describe_error(httpx.ConnectError("c", request=request)) == (
        "connection failed"
    )


def test_default_client_honours_the_proxy_environment(monkeypatch):
    """The transport hook is None outside tests, and httpx then mounts the
    proxy from the environment. A refactor that passes an explicit transport
    would silently bypass the production proxy; this pins the assumption."""
    assert graph_backend.TRANSPORT is None and mail_oauth2.TRANSPORT is None
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.internal:3128")
    with httpx.Client(transport=graph_backend.TRANSPORT) as client:
        pools = {type(t._pool).__name__ for t in client._mounts.values() if t}
    assert "HTTPProxy" in pools


def test_token_error_names_the_proxy(settings, monkeypatch):
    def refuse(request):
        raise httpx.ProxyError("407 Proxy Authentication Required", request=request)

    monkeypatch.setattr(mail_oauth2, "TRANSPORT", httpx.MockTransport(refuse))
    configure(settings)
    result = mailer.send_test("admin@tests.local")
    assert result.ok is False
    assert result.skipped == [
        ("default", "token endpoint unreachable: the HTTP proxy refused the connection")
    ]
