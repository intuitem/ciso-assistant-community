"""Tests for audit-log → SIEM forwarding (Phase 1: OCSF body + dispatch)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from auditlog.models import LogEntry
from core.models import Perimeter
from iam.models import Folder
from webhooks import tasks
from webhooks.models import WebhookEndpoint
from webhooks.ocsf import log_entry_to_ocsf


@pytest.fixture
def root_folder(db):
    folder, _ = Folder.objects.get_or_create(
        content_type=Folder.ContentType.ROOT, defaults={"name": "Global"}
    )
    return folder


@pytest.fixture
def domain_folder(db, root_folder):
    return Folder.objects.create(
        name="Domain A",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=root_folder,
        create_iam_groups=False,
    )


def _make_audit_sink(folder, **kwargs):
    with override_settings(WEBHOOK_ALLOW_PRIVATE_IPS=True):
        defaults = dict(
            name="siem",
            url="https://siem.example/collector",
            kind=WebhookEndpoint.Kind.AUDIT_SINK,
            transport=WebhookEndpoint.Transport.HTTP,
            body_format=WebhookEndpoint.BodyFormat.OCSF,
            headers={"Authorization": "Splunk token"},
            is_active=True,
            folder=folder,
        )
        defaults.update(kwargs)
        return WebhookEndpoint.objects.create(**defaults)


def _create_entry(name, folder):
    p = Perimeter.objects.create(name=name, folder=folder)
    return p, LogEntry.objects.get(object_pk=str(p.pk), action=LogEntry.Action.CREATE)


@pytest.mark.django_db
def test_ocsf_mapping_for_create(root_folder):
    p, le = _create_entry("P-ocsf", root_folder)
    body = log_entry_to_ocsf(le)
    assert body["class_uid"] == 6003
    assert body["category_uid"] == 6
    assert body["activity_id"] == 1  # CREATE -> OCSF Create
    assert body["type_uid"] == 600301
    assert body["api"]["operation"] == "create"
    assert body["api"]["service"]["name"] == "perimeter"
    assert body["resources"][0]["uid"] == str(p.pk)
    assert body["unmapped"]["folder_id"] == str(root_folder.id)


@pytest.mark.django_db
def test_ocsf_activity_remap_for_update_and_delete(root_folder):
    p, _ = _create_entry("P-rm", root_folder)
    p.name = "P-rm-2"
    p.save()
    pk = p.pk
    p.delete()
    upd = LogEntry.objects.get(object_pk=str(pk), action=LogEntry.Action.UPDATE)
    dele = LogEntry.objects.get(object_pk=str(pk), action=LogEntry.Action.DELETE)
    assert log_entry_to_ocsf(upd)["activity_id"] == 3  # UPDATE -> OCSF Update
    assert log_entry_to_ocsf(dele)["activity_id"] == 4  # DELETE -> OCSF Delete
    # delete still carries the folder (Phase 0 get_additional_data fix)
    assert log_entry_to_ocsf(dele)["unmapped"]["folder_id"] == str(root_folder.id)


@pytest.mark.django_db
def test_ocsf_surfaces_correlation_id(root_folder):
    from auditlog.cid import correlation_id

    correlation_id.set("req-abc-123")
    try:
        _, le = _create_entry("P-cid", root_folder)
    finally:
        correlation_id.set(None)
    assert le.cid == "req-abc-123"
    assert log_entry_to_ocsf(le)["metadata"]["correlation_uid"] == "req-abc-123"


@pytest.mark.django_db
def test_ocsf_omits_correlation_uid_when_absent(root_folder):
    _, le = _create_entry("P-no-cid", root_folder)
    assert le.cid is None
    assert "correlation_uid" not in log_entry_to_ocsf(le)["metadata"]


@pytest.mark.django_db
def test_dispatch_selects_unscoped_sink(root_folder):
    ep = _make_audit_sink(root_folder)  # no target_folders -> applies everywhere
    _, le = _create_entry("P-d", root_folder)
    with (
        patch.object(tasks, "ff_is_enabled", return_value=True),
        patch.object(tasks, "send_audit_request") as send,
    ):
        tasks.dispatch_audit_event.call_local(str(le.pk))
    assert send.schedule.call_count == 1
    args = send.schedule.call_args.kwargs["args"]
    assert args[0] == str(ep.id)
    assert args[1]["class_uid"] == 6003


@pytest.mark.django_db
def test_dispatch_skips_when_flag_disabled(root_folder):
    _make_audit_sink(root_folder)
    _, le = _create_entry("P-off", root_folder)
    with (
        patch.object(tasks, "ff_is_enabled", return_value=False),
        patch.object(tasks, "send_audit_request") as send,
    ):
        tasks.dispatch_audit_event.call_local(str(le.pk))
    send.schedule.assert_not_called()


@pytest.mark.django_db
def test_dispatch_respects_folder_scope(root_folder, domain_folder):
    ep = _make_audit_sink(root_folder)
    ep.target_folders.add(domain_folder)

    # object in root (outside scope) -> not selected
    _, le = _create_entry("P-scope-out", root_folder)
    with (
        patch.object(tasks, "ff_is_enabled", return_value=True),
        patch.object(tasks, "send_audit_request") as send,
    ):
        tasks.dispatch_audit_event.call_local(str(le.pk))
    send.schedule.assert_not_called()

    # object in the scoped folder -> selected
    _, le2 = _create_entry("P-scope-in", domain_folder)
    with (
        patch.object(tasks, "ff_is_enabled", return_value=True),
        patch.object(tasks, "send_audit_request") as send,
    ):
        tasks.dispatch_audit_event.call_local(str(le2.pk))
    assert send.schedule.call_count == 1


@pytest.mark.django_db
def test_integration_endpoint_not_selected_for_audit(root_folder):
    _make_audit_sink(root_folder, kind=WebhookEndpoint.Kind.INTEGRATION)
    _, le = _create_entry("P-int", root_folder)
    with (
        patch.object(tasks, "ff_is_enabled", return_value=True),
        patch.object(tasks, "send_audit_request") as send,
    ):
        tasks.dispatch_audit_event.call_local(str(le.pk))
    send.schedule.assert_not_called()


@pytest.mark.django_db
def test_replay_schedules_entries_since(root_folder):
    ep = _make_audit_sink(root_folder)
    _create_entry("P-replay-1", root_folder)
    _create_entry("P-replay-2", root_folder)
    since = datetime(2000, 1, 1, tzinfo=timezone.utc)
    with patch.object(tasks, "send_audit_request") as send:
        result = tasks.replay_audit_to_sink(ep, since)
    assert result["scheduled"] == send.schedule.call_count == result["total"]
    assert result["scheduled"] >= 2
    assert result["truncated"] is False


@pytest.mark.django_db
def test_replay_truncates_with_flag(root_folder):
    ep = _make_audit_sink(root_folder)
    _create_entry("P-cap-1", root_folder)
    _create_entry("P-cap-2", root_folder)
    since = datetime(2000, 1, 1, tzinfo=timezone.utc)
    with patch.object(tasks, "send_audit_request") as send:
        result = tasks.replay_audit_to_sink(ep, since, cap=1)
    assert result["scheduled"] == 1
    assert result["truncated"] is True
    assert result["total"] >= 2
    assert send.schedule.call_count == 1


@pytest.mark.django_db
def test_replay_respects_folder_scope(root_folder, domain_folder):
    ep = _make_audit_sink(root_folder)
    ep.target_folders.add(domain_folder)
    p_out, _ = _create_entry("P-root-only", root_folder)  # outside scope
    _create_entry("P-in-domain", domain_folder)  # in scope
    since = datetime(2000, 1, 1, tzinfo=timezone.utc)
    with patch.object(tasks, "send_audit_request") as send:
        result = tasks.replay_audit_to_sink(ep, since)
    # Only in-scope entries (folder_id == domain) are forwarded. Derive the
    # expected count from the DB — the domain folder's own creation entry is
    # also in scope, so a hardcoded count is brittle.
    expected = (
        LogEntry.objects.filter(additional_data__folder_id=str(domain_folder.id))
        .exclude(action=LogEntry.Action.ACCESS)
        .count()
    )
    assert result["scheduled"] == send.schedule.call_count == expected
    assert expected >= 1
    # the out-of-scope (root) perimeter must not be forwarded
    assert not LogEntry.objects.filter(
        object_pk=str(p_out.pk), additional_data__folder_id=str(domain_folder.id)
    ).exists()


@pytest.mark.django_db
@override_settings(WEBHOOK_ALLOW_PRIVATE_IPS=True)
def test_send_audit_request_uses_static_headers_no_hmac(root_folder):
    ep = _make_audit_sink(root_folder)
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch("webhooks.tasks.requests.post", return_value=mock_response) as post:
        result = tasks.send_audit_request.call_local(str(ep.id), {"class_uid": 6003})
    assert result.startswith("Success")
    sent_headers = post.call_args.kwargs["headers"]
    assert sent_headers["Authorization"] == "Splunk token"  # static auth, not HMAC
    assert not any(h.startswith("webhook-") for h in sent_headers)  # no HMAC envelope


@pytest.mark.django_db
def test_dispatch_routes_to_kafka_transport(root_folder):
    ep = _make_audit_sink(
        root_folder,
        transport=WebhookEndpoint.Transport.KAFKA,
        kafka_config={"bootstrap_servers": "kafka:9092", "topic": "audit"},
    )
    _, le = _create_entry("P-kafka", root_folder)
    with (
        patch.object(tasks, "ff_is_enabled", return_value=True),
        patch.object(tasks, "send_audit_to_kafka") as kafka_send,
        patch.object(tasks, "send_audit_request") as http_send,
    ):
        tasks.dispatch_audit_event.call_local(str(le.pk))
    assert kafka_send.schedule.call_count == 1
    http_send.schedule.assert_not_called()
    assert kafka_send.schedule.call_args.kwargs["args"][0] == str(ep.id)


@pytest.mark.django_db
def test_send_audit_to_kafka_produces(root_folder):
    ep = _make_audit_sink(
        root_folder,
        transport=WebhookEndpoint.Transport.KAFKA,
        kafka_config={
            "bootstrap_servers": "kafka:9092",
            "topic": "audit-topic",
            "config": {"security_protocol": "SASL_SSL"},
        },
    )
    producer = MagicMock()
    with patch.object(tasks, "_make_producer", return_value=producer) as make:
        result = tasks.send_audit_to_kafka.call_local(str(ep.id), {"class_uid": 6003})
    assert result.startswith("Success")
    make.assert_called_once()
    (topic,) = producer.send.call_args.args
    assert topic == "audit-topic"
    assert producer.send.call_args.kwargs["value"] == b'{"class_uid":6003}'
    producer.send.return_value.get.assert_called_once()  # delivery confirmed
    producer.close.assert_called_once()


@pytest.mark.django_db
def test_send_audit_to_kafka_misconfigured(root_folder):
    ep = _make_audit_sink(
        root_folder, transport=WebhookEndpoint.Transport.KAFKA, kafka_config={}
    )
    with patch.object(tasks, "_make_producer") as make:
        result = tasks.send_audit_to_kafka.call_local(str(ep.id), {"class_uid": 6003})
    assert result.startswith("Misconfigured")
    make.assert_not_called()


@pytest.mark.django_db
def test_serializer_hides_secrets(root_folder):
    from webhooks.serializers import AuditSinkSerializer

    ep = _make_audit_sink(
        root_folder,
        transport=WebhookEndpoint.Transport.KAFKA,
        headers={"Authorization": "Splunk token"},
        kafka_config={
            "bootstrap_servers": "b:9092",
            "topic": "t",
            "config": {"sasl_plain_username": "u", "sasl_plain_password": "secret"},
        },
    )
    data = AuditSinkSerializer(ep).data
    assert "headers" not in data
    assert data["has_headers"] is True
    assert data["has_sasl_password"] is True
    # username kept for prefill, password stripped
    assert data["kafka_config"]["config"]["sasl_plain_username"] == "u"
    assert "sasl_plain_password" not in data["kafka_config"]["config"]


@pytest.mark.django_db
def test_update_preserves_sasl_password_when_blank(root_folder):
    from webhooks.serializers import AuditSinkSerializer

    ep = _make_audit_sink(
        root_folder,
        transport=WebhookEndpoint.Transport.KAFKA,
        kafka_config={
            "bootstrap_servers": "b:9092",
            "topic": "t",
            "config": {"sasl_plain_username": "u", "sasl_plain_password": "secret"},
        },
    )
    serializer = AuditSinkSerializer()
    serializer.update(
        ep,
        {
            "kafka_config": {
                "bootstrap_servers": "b:9092",
                "topic": "t2",
                "config": {"sasl_plain_username": "u"},
            }
        },
    )
    ep.refresh_from_db()
    assert ep.kafka_config["topic"] == "t2"
    assert ep.kafka_config["config"]["sasl_plain_password"] == "secret"


@pytest.mark.django_db
def test_get_additional_data_survives_cascade_doesnotexist(root_folder):
    # get_additional_data runs in auditlog's synchronous delete receiver; a
    # cascade may have removed the FK target get_folder traverses. It must
    # degrade to folder_id=None instead of raising into the delete.
    p = Perimeter(name="ghost")
    p.folder_id = None
    with patch.object(Folder, "get_folder", side_effect=Folder.DoesNotExist):
        assert p.get_additional_data() == {"folder_id": None}


@pytest.mark.django_db
def test_update_preserves_headers_when_omitted(root_folder):
    from webhooks.serializers import AuditSinkSerializer

    ep = _make_audit_sink(root_folder, headers={"Authorization": "Splunk token"})
    with override_settings(WEBHOOK_ALLOW_PRIVATE_IPS=True):
        AuditSinkSerializer().update(ep, {"url": "https://siem.example/v2"})
    ep.refresh_from_db()
    assert ep.url == "https://siem.example/v2"
    assert ep.headers == {"Authorization": "Splunk token"}
