"""End-to-end OAuth2 client-credentials check over a real loopback socket.

No mocks on the HTTP path: a throwaway server plays both the token endpoint and
an Azure-Monitor-shaped collector, so requests, token parsing, the bearer header
and the array envelope are all exercised for real.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import pytest
from django.test import override_settings

from iam.models import Folder
from webhooks import oauth, tasks
from webhooks.models import WebhookEndpoint

# Recorded per run: token requests seen, collector requests seen.
STATE = {}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode()

        if self.path.startswith("/token"):
            STATE["tokens"].append(parse_qs(raw))
            issued = f"tok-{len(STATE['tokens'])}"
            return self._json(200, {"access_token": issued, "expires_in": 3600})

        STATE["ingest"].append(
            {
                "path": self.path,
                "auth": self.headers.get("Authorization"),
                "content_type": self.headers.get("Content-Type"),
                "body": json.loads(raw),
            }
        )
        # First call rejects the token once, to exercise the refresh path.
        if STATE["reject_first"] and len(STATE["ingest"]) == 1:
            return self._json(401, {"error": "expired"})
        return self._json(204, {})


@pytest.fixture
def collector():
    STATE.clear()
    STATE.update(tokens=[], ingest=[], reject_first=False)
    oauth._cache.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    oauth._cache.clear()


@pytest.fixture
def root_folder(db):
    folder, _ = Folder.objects.get_or_create(
        content_type=Folder.ContentType.ROOT, defaults={"name": "Global"}
    )
    return folder


def _sink(folder, base):
    with override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True):
        return WebhookEndpoint.objects.create(
            name="sentinel",
            # Shaped like a real DCE call, query string included.
            url=f"{base}/dataCollectionRules/dcr-abc/streams/Custom-Audit_CL"
            "?api-version=2023-01-01",
            kind=WebhookEndpoint.Kind.AUDIT_SINK,
            transport=WebhookEndpoint.Transport.HTTP,
            body_format=WebhookEndpoint.BodyFormat.OCSF,
            body_wrapper=WebhookEndpoint.BodyWrapper.ARRAY,
            auth_type=WebhookEndpoint.AuthType.OAUTH2_CC,
            oauth_config={
                "token_url": f"{base}/token",
                "client_id": "app-id",
                "client_secret": "app-secret",
                "scope": "https://monitor.azure.com//.default",
            },
            folder=folder,
        )


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_loopback_oauth_and_array_envelope(collector, root_folder):
    ep = _sink(root_folder, collector)
    result = tasks.send_audit_request.call_local(str(ep.id), {"class_uid": 6003})

    assert result.startswith("Success")

    token_request = STATE["tokens"][0]
    assert token_request["grant_type"] == ["client_credentials"]
    assert token_request["client_id"] == ["app-id"]
    assert token_request["client_secret"] == ["app-secret"]
    assert token_request["scope"] == ["https://monitor.azure.com//.default"]

    sent = STATE["ingest"][0]
    assert sent["auth"] == "Bearer tok-1"
    assert sent["content_type"] == "application/json"
    assert sent["path"].endswith("?api-version=2023-01-01")
    assert sent["body"] == [{"class_uid": 6003}]


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_loopback_refreshes_token_after_401(collector, root_folder):
    STATE["reject_first"] = True
    ep = _sink(root_folder, collector)
    result = tasks.send_audit_request.call_local(str(ep.id), {"class_uid": 6003})

    assert result.startswith("Success")
    assert len(STATE["tokens"]) == 2  # minted, rejected, re-minted
    assert STATE["ingest"][0]["auth"] == "Bearer tok-1"
    assert STATE["ingest"][1]["auth"] == "Bearer tok-2"


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_loopback_reuses_cached_token(collector, root_folder):
    ep = _sink(root_folder, collector)
    tasks.send_audit_request.call_local(str(ep.id), {"a": 1})
    tasks.send_audit_request.call_local(str(ep.id), {"a": 2})

    assert len(STATE["tokens"]) == 1
    assert len(STATE["ingest"]) == 2
