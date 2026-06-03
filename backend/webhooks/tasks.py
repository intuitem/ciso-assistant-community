import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone

import requests
from huey.contrib.djhuey import db_task
from django.core.serializers.json import DjangoJSONEncoder

from core.net_safety import BlockedRequestError, assert_public_url_unless_dev

from .models import WebhookEndpoint

import structlog

logger = structlog.get_logger(__name__)


@db_task(retries=5, retry_delay=60, retry_backoff=2.0)
def send_webhook_request(endpoint_id, event_type, data_payload):
    """
    Huey task to send a single webhook event.
    This task will be retried on failure.
    """
    try:
        endpoint = WebhookEndpoint.objects.get(id=endpoint_id, is_active=True)
    except WebhookEndpoint.DoesNotExist:
        logger.warning("Endpoint deleted. Task aborted.", endpoint_id=endpoint_id)
        return

    # Build payload
    timestamp_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    full_payload = {
        "type": event_type,
        "timestamp": timestamp_iso,  # Event occurrence timestamp
        "data": data_payload,
    }

    # Send minified JSON, as recommended
    json_payload = json.dumps(
        full_payload, separators=(",", ":"), cls=DjangoJSONEncoder
    )

    # Generate headers & signature
    webhook_id = f"msg_{secrets.token_hex(16)}"
    timestamp_unix = str(int(time.time()))

    content_to_sign = f"{webhook_id}.{timestamp_unix}.{json_payload}"

    digest = hmac.new(
        endpoint.secret.encode("utf-8"), content_to_sign.encode("utf-8"), hashlib.sha256
    ).digest()

    signature = base64.b64encode(digest).decode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "webhook-id": webhook_id,
        "webhook-timestamp": timestamp_unix,
        "webhook-signature": f"v1,{signature}",
    }

    # Re-validate at send time: model.clean() only blocks IP-literal
    # hostnames, so DNS-based targets and post-save DNS changes need
    # this. DnsLookupError is transient and propagates so Huey retries.
    try:
        assert_public_url_unless_dev(endpoint.url, allowed_schemes=("http", "https"))
    except BlockedRequestError:
        # Terminal: return (not raise) so Huey doesn't retry 5x with a
        # fresh webhook-id — receivers would see those as distinct.
        logger.error(
            "Webhook blocked by SSRF guard",
            endpoint_id=endpoint_id,
            exc_info=True,
        )
        return f"Blocked: {endpoint_id} URL points to a non-public address"

    try:
        response = requests.post(
            endpoint.url,
            data=json_payload.encode("utf-8"),
            headers=headers,
            timeout=15,
            allow_redirects=False,
        )

        if 200 <= response.status_code < 300:
            return f"Success: Sent {event_type} to {endpoint.url}"
        elif 300 <= response.status_code < 400:
            # Terminal (same reason as the SSRF-block branch above).
            logger.warning(
                "Webhook target returned redirect; not followed",
                endpoint_id=endpoint_id,
                status_code=response.status_code,
            )
            return (
                f"Blocked redirect: {endpoint_id} returned "
                f"status {response.status_code}"
            )
        else:
            raise Exception(
                f"Webhook failed for {endpoint_id} with status {response.status_code}."
            )

    except requests.exceptions.RequestException as e:
        # Network error, timeout, etc.
        # Raise exception to trigger Huey retry
        raise Exception(f"Webhook network error for {endpoint_id}: {e}")
