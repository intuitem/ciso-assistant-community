import base64
import hashlib
import hmac
import json
import secrets
import socket
import ssl
import time
from datetime import datetime, timezone

import requests
from huey.contrib.djhuey import db_task
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q, Count

from auditlog.models import LogEntry
from core.net_safety import BlockedRequestError, assert_public_url_unless_dev
from global_settings.utils import ff_is_enabled
from iam.models import Folder

from .models import WebhookEndpoint
from .ocsf import build_audit_body

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


def _deliver(endpoint, body):
    # Route an audit event to the sink's transport.
    if endpoint.transport == WebhookEndpoint.Transport.KAFKA:
        send_audit_to_kafka.schedule(args=(str(endpoint.id), body), delay=1)
    elif endpoint.transport == WebhookEndpoint.Transport.SYSLOG:
        send_audit_to_syslog.schedule(args=(str(endpoint.id), body), delay=1)
    else:
        send_audit_request.schedule(args=(str(endpoint.id), body), delay=1)


@db_task()
def dispatch_audit_event(log_entry_pk):
    # Fan one audit LogEntry out to every active audit-sink whose folder scope
    # matches (no target_folders = all folders).
    if not ff_is_enabled("audit_log_forwarding"):
        return
    try:
        log_entry = LogEntry.objects.select_related("content_type").get(pk=log_entry_pk)
    except LogEntry.DoesNotExist:
        return

    folder_id = (log_entry.additional_data or {}).get("folder_id")
    folder = Folder.objects.filter(id=folder_id).first() if folder_id else None

    endpoints = (
        WebhookEndpoint.objects.annotate(folder_count=Count("target_folders"))
        .filter(
            Q(folder_count=0) | Q(target_folders=folder),
            kind=WebhookEndpoint.Kind.AUDIT_SINK,
            is_active=True,
        )
        .distinct()
    )

    for endpoint in endpoints:
        _deliver(endpoint, build_audit_body(log_entry, endpoint.body_format))


@db_task(retries=5, retry_delay=60, retry_backoff=2.0)
def send_audit_request(endpoint_id, body):
    """
    Deliver one audit event to a SIEM HTTP endpoint. Unlike send_webhook_request,
    there is no HMAC envelope: the body is the canonical event (OCSF by default)
    and auth is the endpoint's static headers (e.g. a Splunk HEC token).
    """
    try:
        endpoint = WebhookEndpoint.objects.get(id=endpoint_id, is_active=True)
    except WebhookEndpoint.DoesNotExist:
        logger.warning("Audit sink deleted. Task aborted.", endpoint_id=endpoint_id)
        return

    json_payload = json.dumps(body, separators=(",", ":"), cls=DjangoJSONEncoder)
    headers = {"Content-Type": "application/json", **(endpoint.headers or {})}

    # Re-validate at send time (DNS-based targets, post-save DNS changes).
    try:
        assert_public_url_unless_dev(endpoint.url, allowed_schemes=("http", "https"))
    except BlockedRequestError:
        logger.error(
            "Audit sink blocked by SSRF guard",
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
            return f"Success: Sent audit event to {endpoint.url}"
        elif 300 <= response.status_code < 400:
            logger.warning(
                "Audit sink returned redirect; not followed",
                endpoint_id=endpoint_id,
                status_code=response.status_code,
            )
            return f"Blocked redirect: {endpoint_id} returned {response.status_code}"
        else:
            raise Exception(
                f"Audit sink failed for {endpoint_id} with status {response.status_code}."
            )
    except requests.exceptions.RequestException as e:
        raise Exception(f"Audit sink network error for {endpoint_id}: {e}")


def replay_audit_to_sink(endpoint, since, until=None, cap=None):
    """
    Re-emit historical audit events to a single sink (the replay/backfill path).
    LogEntry is the system of record, so a sink that was down can be backfilled.
    Bounded by AUDITLOG_MAX_RECORDS with a logged (never silent) truncation.
    """
    cap = cap or getattr(settings, "AUDITLOG_MAX_RECORDS", 50000)
    entries = LogEntry.objects.exclude(action=LogEntry.Action.ACCESS).filter(
        timestamp__gte=since
    )
    if until:
        entries = entries.filter(timestamp__lte=until)

    target_folder_ids = [str(f.id) for f in endpoint.target_folders.all()]
    if target_folder_ids:
        entries = entries.filter(additional_data__folder_id__in=target_folder_ids)
    entries = entries.order_by("timestamp")

    total = entries.count()
    truncated = total > cap
    if truncated:
        logger.warning(
            "Audit replay truncated to cap",
            endpoint_id=str(endpoint.id),
            total=total,
            cap=cap,
        )

    scheduled = 0
    for entry in entries[:cap].iterator():
        _deliver(endpoint, build_audit_body(entry, endpoint.body_format))
        scheduled += 1

    return {"scheduled": scheduled, "truncated": truncated, "total": total}


def _make_producer(cfg):
    # kafka-python, matching the dispatcher's config vocabulary (security_protocol,
    # sasl_mechanism, sasl_plain_username/password live in cfg["config"]).
    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=cfg["bootstrap_servers"], **cfg.get("config", {})
    )


@db_task(retries=5, retry_delay=60, retry_backoff=2.0)
def send_audit_to_kafka(endpoint_id, body):
    try:
        endpoint = WebhookEndpoint.objects.get(id=endpoint_id, is_active=True)
    except WebhookEndpoint.DoesNotExist:
        logger.warning("Audit sink deleted. Task aborted.", endpoint_id=endpoint_id)
        return

    cfg = endpoint.kafka_config or {}
    if not cfg.get("bootstrap_servers") or not cfg.get("topic"):
        logger.error("Kafka sink misconfigured", endpoint_id=endpoint_id)
        return f"Misconfigured: {endpoint_id} missing bootstrap_servers/topic"

    payload = json.dumps(body, separators=(",", ":"), cls=DjangoJSONEncoder).encode(
        "utf-8"
    )
    producer = _make_producer(cfg)
    try:
        # .get() raises KafkaError on delivery failure, so Huey retries.
        producer.send(cfg["topic"], value=payload).get(timeout=15)
    finally:
        producer.close(timeout=5)
    return f"Success: produced audit event to {cfg['topic']}"


def _syslog_frame(body) -> bytes:
    # CEF/LEEF builders return a str; JSON formats return a dict.
    msg = (
        body
        if isinstance(body, str)
        else json.dumps(body, separators=(",", ":"), cls=DjangoJSONEncoder)
    )
    pri = 13 * 8 + 6  # facility 13 (log audit), severity 6 (info)
    return f"<{pri}>{msg}".encode("utf-8")


@db_task(retries=5, retry_delay=60, retry_backoff=2.0)
def send_audit_to_syslog(endpoint_id, body):
    try:
        endpoint = WebhookEndpoint.objects.get(id=endpoint_id, is_active=True)
    except WebhookEndpoint.DoesNotExist:
        logger.warning("Audit sink deleted. Task aborted.", endpoint_id=endpoint_id)
        return

    cfg = endpoint.syslog_config or {}
    host = cfg.get("host")
    proto = (cfg.get("protocol") or "tcp").lower()
    port = int(cfg.get("port") or (6514 if proto == "tls" else 514))
    if not host:
        logger.error("Syslog sink misconfigured", endpoint_id=endpoint_id)
        return f"Misconfigured: {endpoint_id} missing host"

    try:
        assert_public_url_unless_dev(
            f"{proto}://{host}:{port}", allowed_schemes=("tcp", "udp", "tls")
        )
    except BlockedRequestError:
        logger.error(
            "Syslog sink blocked by SSRF guard", endpoint_id=endpoint_id, exc_info=True
        )
        return f"Blocked: {endpoint_id} host points to a non-public address"

    frame = _syslog_frame(body)
    try:
        if proto == "udp":
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.sendto(frame, (host, port))
            finally:
                sock.close()
        else:
            sock = socket.create_connection((host, port), timeout=15)
            try:
                if proto == "tls":
                    sock = ssl.create_default_context().wrap_socket(
                        sock, server_hostname=host
                    )
                sock.sendall(
                    frame + b"\n"
                )  # newline framing (RFC 6587 non-transparent)
            finally:
                sock.close()
    except OSError as e:
        raise Exception(f"Syslog network error for {endpoint_id}: {e}")
    return f"Success: sent audit event to {proto}://{host}:{port}"
