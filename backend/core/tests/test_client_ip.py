"""Client IP resolution shared by the login rate limits (iam.adapter), the
audit log (core.custom_middleware) and the workflow webhook throttle: the LAST
X-Forwarded-For entry, added by the hop just in front of the backend (the
frontend or the reverse proxy), else REMOTE_ADDR. Leading entries are
client-supplied and never trusted."""

import ipaddress

import pytest
from auditlog.models import LogEntry
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from automation.workflows.views import WebhookRateThrottle
from core.custom_middleware import AuditlogMiddleware, parse_ip, resolve_client_ip
from core.models import Asset
from iam.models import Folder


def make_request(xff=None, remote="10.0.0.9"):
    extra = {"REMOTE_ADDR": remote}
    if xff is not None:
        extra["HTTP_X_FORWARDED_FOR"] = xff
    return RequestFactory().get("/", **extra)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1.2.3.4", "1.2.3.4"),
        (" 1.2.3.4 ", "1.2.3.4"),
        ("1.2.3.4:5678", "1.2.3.4"),
        ("2001:db8::1", "2001:db8::1"),
        ("[2001:db8::1]", "2001:db8::1"),
        ("[2001:db8::1]:443", "2001:db8::1"),
        ("::ffff:1.2.3.4", "1.2.3.4"),
    ],
)
def test_parse_ip_accepts(raw, expected):
    assert parse_ip(raw) == ipaddress.ip_address(expected)


@pytest.mark.parametrize("raw", ["", None, "unknown", "1.2.3", "1.2.3.4.5"])
def test_parse_ip_rejects(raw):
    assert parse_ip(raw) is None


@pytest.mark.parametrize(
    "xff, remote, expected",
    [
        (None, "10.0.0.9", "10.0.0.9"),
        ("", "10.0.0.9", "10.0.0.9"),
        ("203.0.113.7", "10.0.0.9", "203.0.113.7"),
        # Leading entries are client-supplied: only the last one counts.
        ("198.51.100.1, 203.0.113.7", "10.0.0.9", "203.0.113.7"),
        # A malformed last entry discards the whole header.
        ("203.0.113.7, garbage", "10.0.0.9", "10.0.0.9"),
        (None, "", None),
    ],
)
def test_resolve_client_ip(xff, remote, expected):
    assert resolve_client_ip(make_request(xff=xff, remote=remote)) == expected


def test_resolve_client_ip_without_request():
    assert resolve_client_ip(None) is None


def test_webhook_throttle_keys_on_the_resolved_client_ip():
    request = make_request(xff="198.51.100.1, 203.0.113.7:5555")

    key = WebhookRateThrottle().get_cache_key(request, view=None)

    assert key == "throttle_workflow_webhook_203.0.113.7"


@pytest.mark.django_db
def test_audit_log_records_the_resolved_client_ip():
    # auditlog's own resolver takes the FIRST (client-supplied) entry.
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    folder = Folder.objects.create(
        name="Domain IP",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=root,
        create_iam_groups=False,
    )
    created = {}

    def view(request):
        created["asset"] = Asset.objects.create(name="A-ip", folder=folder)
        return HttpResponse()

    request = make_request(xff="198.51.100.1, 203.0.113.7")
    request.user = AnonymousUser()
    AuditlogMiddleware(view)(request)

    entry = LogEntry.objects.get(
        object_pk=str(created["asset"].pk), action=LogEntry.Action.CREATE
    )
    assert entry.remote_addr == "203.0.113.7"
