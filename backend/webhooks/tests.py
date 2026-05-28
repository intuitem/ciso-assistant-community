"""Tests for SSRF guard + redirect refusal in webhook delivery."""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from core.net_safety import DnsLookupError
from webhooks.models import WebhookEndpoint
from webhooks.tasks import send_webhook_request


@pytest.fixture
def public_endpoint(db):
    with override_settings(WEBHOOK_ALLOW_PRIVATE_IPS=True):
        return WebhookEndpoint.objects.create(
            name="public",
            url="https://example.com/hook",
            secret="x" * 32,
            is_active=True,
        )


@pytest.fixture
def private_endpoint(db):
    """WebhookEndpoint pointing at a private IP. Bypasses the save-time
    guard via WEBHOOK_ALLOW_PRIVATE_IPS to simulate a pre-existing
    record or post-save DNS flip."""
    with override_settings(WEBHOOK_ALLOW_PRIVATE_IPS=True):
        return WebhookEndpoint.objects.create(
            name="private",
            url="http://10.0.0.1/admin",
            secret="x" * 32,
            is_active=True,
        )


@pytest.mark.django_db
@override_settings(WEBHOOK_ALLOW_PRIVATE_IPS=False)
def test_blocked_url_returns_terminally(private_endpoint):
    # Permanent policy denial must be terminal: return (not raise) so
    # Huey doesn't retry 5x with fresh webhook-ids.
    result = send_webhook_request.call_local(
        private_endpoint.id, "test.event", {"foo": "bar"}
    )
    assert result.startswith("Blocked")


@pytest.mark.django_db
@override_settings(WEBHOOK_ALLOW_PRIVATE_IPS=False)
def test_redirect_returns_terminally(public_endpoint):
    # 3xx must not be followed and must not trigger retries — each
    # retry would mint a new webhook-id, so a 307/308 target would see
    # distinct deliveries.
    mock_response = MagicMock()
    mock_response.status_code = 302
    mock_response.headers = {"Location": "https://elsewhere.example/"}

    with patch("webhooks.tasks.requests.post", return_value=mock_response):
        result = send_webhook_request.call_local(
            public_endpoint.id, "test.event", {"foo": "bar"}
        )
    assert "redirect" in result.lower()


@pytest.mark.django_db
@override_settings(WEBHOOK_ALLOW_PRIVATE_IPS=False)
def test_dns_failure_is_transient_and_propagates(public_endpoint):
    # DnsLookupError must propagate so Huey retries; it must NOT be
    # caught by the BlockedRequestError handler.
    with patch(
        "webhooks.tasks.assert_public_url_unless_dev",
        side_effect=DnsLookupError("DNS lookup failed for example.com"),
    ):
        with pytest.raises(DnsLookupError):
            send_webhook_request.call_local(
                public_endpoint.id, "test.event", {"foo": "bar"}
            )


@pytest.mark.django_db
@override_settings(WEBHOOK_ALLOW_PRIVATE_IPS=False)
def test_5xx_raises_for_retry(public_endpoint):
    # Non-redirect non-2xx must raise so Huey retries the transient
    # remote failure.
    mock_response = MagicMock()
    mock_response.status_code = 503

    with patch("webhooks.tasks.requests.post", return_value=mock_response):
        with pytest.raises(Exception, match="status 503"):
            send_webhook_request.call_local(
                public_endpoint.id, "test.event", {"foo": "bar"}
            )


@pytest.mark.django_db
@override_settings(WEBHOOK_ALLOW_PRIVATE_IPS=True)
def test_allow_private_ips_bypasses_guard(private_endpoint):
    # Dev escape hatch: the SSRF check is skipped.
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("webhooks.tasks.requests.post", return_value=mock_response):
        result = send_webhook_request.call_local(
            private_endpoint.id, "test.event", {"foo": "bar"}
        )
    assert result.startswith("Success")
