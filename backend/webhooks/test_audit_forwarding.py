"""Tests for audit-log → SIEM forwarding (Phase 1: OCSF body + dispatch)."""

import json
import time
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
    with override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True):
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
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
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


def test_validate_kafka_requires_bootstrap_and_topic():
    from rest_framework import serializers as drf
    from webhooks.serializers import AuditSinkSerializer

    s = AuditSinkSerializer()
    with pytest.raises(drf.ValidationError):
        s.validate(
            {
                "transport": WebhookEndpoint.Transport.KAFKA,
                "kafka_config": {"config": {}},
            }
        )
    out = s.validate(
        {
            "transport": WebhookEndpoint.Transport.KAFKA,
            "kafka_config": {"bootstrap_servers": "b:9092", "topic": "t"},
        }
    )
    assert out["transport"] == WebhookEndpoint.Transport.KAFKA


def test_validate_headers_rejects_non_string_values():
    from rest_framework import serializers as drf
    from webhooks.serializers import AuditSinkSerializer

    s = AuditSinkSerializer()
    with pytest.raises(drf.ValidationError):
        s.validate_headers({"X": {"nested": 1}})
    assert s.validate_headers({"Authorization": "Splunk t"}) == {
        "Authorization": "Splunk t"
    }


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
    with override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True):
        AuditSinkSerializer().update(ep, {"url": "https://siem.example/v2"})
    ep.refresh_from_db()
    assert ep.url == "https://siem.example/v2"
    assert ep.headers == {"Authorization": "Splunk token"}


# --- OAuth 2.0 client credentials + body envelope ---------------------------


@pytest.fixture(autouse=True)
def _clear_oauth_cache():
    from webhooks import oauth

    oauth._cache.clear()
    yield
    oauth._cache.clear()


def _oauth_sink(folder, **kwargs):
    return _make_audit_sink(
        folder,
        headers={},
        auth_type=WebhookEndpoint.AuthType.OAUTH2_CC,
        oauth_config={
            "token_url": "https://login.microsoftonline.com/t/oauth2/v2.0/token",
            "client_id": "cid",
            "client_secret": "csecret",
            "scope": "https://monitor.azure.com//.default",
        },
        **kwargs,
    )


def _token_response(token="tok", expires_in=3600):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"access_token": token, "expires_in": expires_in}
    return response


def _minted(token):
    return (token, time.monotonic() + 3600)


# webhooks.tasks.requests and webhooks.oauth.requests are the same module object,
# so patching both paths in one test collides. Delivery tests stub oauth._fetch;
# the token request itself is covered by the oauth-module tests below.


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_send_audit_request_sends_oauth_bearer(root_folder):
    ep = _oauth_sink(root_folder)
    sink_response = MagicMock()
    sink_response.status_code = 200
    with patch("webhooks.oauth._fetch", return_value=_minted("tok")):
        with patch("webhooks.tasks.requests.post", return_value=sink_response) as post:
            result = tasks.send_audit_request.call_local(
                str(ep.id), {"class_uid": 6003}
            )

    assert result.startswith("Success")
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer tok"


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_oauth_token_is_cached_across_sends(root_folder):
    ep = _oauth_sink(root_folder)
    sink_response = MagicMock()
    sink_response.status_code = 200
    with patch("webhooks.oauth._fetch", return_value=_minted("tok")) as fetch:
        with patch("webhooks.tasks.requests.post", return_value=sink_response):
            tasks.send_audit_request.call_local(str(ep.id), {"a": 1})
            tasks.send_audit_request.call_local(str(ep.id), {"a": 2})

    assert fetch.call_count == 1


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_oauth_refreshes_once_on_401(root_folder):
    ep = _oauth_sink(root_folder)
    unauthorized = MagicMock()
    unauthorized.status_code = 401
    ok = MagicMock()
    ok.status_code = 200
    with patch(
        "webhooks.oauth._fetch", side_effect=[_minted("stale"), _minted("fresh")]
    ) as fetch:
        with patch(
            "webhooks.tasks.requests.post", side_effect=[unauthorized, ok]
        ) as post:
            result = tasks.send_audit_request.call_local(str(ep.id), {"a": 1})

    assert result.startswith("Success")
    assert fetch.call_count == 2
    assert post.call_args_list[0].kwargs["headers"]["Authorization"] == "Bearer stale"
    assert post.call_args_list[1].kwargs["headers"]["Authorization"] == "Bearer fresh"


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_oauth_failure_propagates_for_retry(root_folder):
    from webhooks.oauth import OAuthError

    ep = _oauth_sink(root_folder)
    with patch("webhooks.oauth._fetch", side_effect=OAuthError("denied")):
        with patch("webhooks.tasks.requests.post") as post:
            with pytest.raises(OAuthError):
                tasks.send_audit_request.call_local(str(ep.id), {"a": 1})
    # The event is never sent unauthenticated.
    post.assert_not_called()


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_static_auth_does_not_fetch_a_token(root_folder):
    ep = _make_audit_sink(root_folder)
    sink_response = MagicMock()
    sink_response.status_code = 200
    with patch("webhooks.oauth._fetch") as fetch:
        with patch("webhooks.tasks.requests.post", return_value=sink_response):
            tasks.send_audit_request.call_local(str(ep.id), {"a": 1})
    fetch.assert_not_called()


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_oauth_token_request_is_an_rfc6749_form_post(root_folder):
    from webhooks import oauth

    ep = _oauth_sink(root_folder)
    with patch("webhooks.oauth.requests.post", return_value=_token_response()) as post:
        assert oauth.get_token(ep) == "tok"

    assert post.call_args.args[0] == ep.oauth_config["token_url"]
    sent = post.call_args.kwargs["data"]
    assert sent["grant_type"] == "client_credentials"
    assert sent["client_id"] == "cid"
    assert sent["client_secret"] == "csecret"
    assert sent["scope"] == "https://monitor.azure.com//.default"


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_oauth_rejects_token_endpoint_error(root_folder):
    from webhooks import oauth

    ep = _oauth_sink(root_folder)
    denied = MagicMock()
    denied.status_code = 401
    with patch("webhooks.oauth.requests.post", return_value=denied):
        with pytest.raises(oauth.OAuthError):
            oauth.get_token(ep)


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_oauth_renews_within_the_expiry_skew(root_folder):
    from webhooks import oauth

    # A lifetime shorter than the skew must never be served from cache.
    ep = _oauth_sink(root_folder)
    with patch(
        "webhooks.oauth.requests.post", return_value=_token_response(expires_in=30)
    ) as post:
        oauth.get_token(ep)
        oauth.get_token(ep)

    assert post.call_count == 2


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_body_wrapper_array_wraps_the_event(root_folder):
    # Azure Monitor Logs Ingestion rejects a bare object.
    ep = _make_audit_sink(root_folder, body_wrapper=WebhookEndpoint.BodyWrapper.ARRAY)
    sink_response = MagicMock()
    sink_response.status_code = 200
    with patch("webhooks.tasks.requests.post", return_value=sink_response) as post:
        tasks.send_audit_request.call_local(str(ep.id), {"class_uid": 6003})

    assert json.loads(post.call_args.kwargs["data"]) == [{"class_uid": 6003}]


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
def test_body_wrapper_none_sends_bare_object(root_folder):
    ep = _make_audit_sink(root_folder)
    sink_response = MagicMock()
    sink_response.status_code = 200
    with patch("webhooks.tasks.requests.post", return_value=sink_response) as post:
        tasks.send_audit_request.call_local(str(ep.id), {"class_uid": 6003})

    assert json.loads(post.call_args.kwargs["data"]) == {"class_uid": 6003}


@pytest.mark.django_db
def test_serializer_hides_client_secret(root_folder):
    from webhooks.serializers import AuditSinkSerializer

    ep = _oauth_sink(root_folder)
    data = AuditSinkSerializer(ep).data
    assert data["has_client_secret"] is True
    assert "client_secret" not in data["oauth_config"]
    # token_url/client_id/scope are kept for edit prefill.
    assert data["oauth_config"]["client_id"] == "cid"
    assert data["oauth_config"]["scope"] == "https://monitor.azure.com//.default"


@pytest.mark.django_db
def test_update_preserves_client_secret_when_blank(root_folder):
    from webhooks.serializers import AuditSinkSerializer

    ep = _oauth_sink(root_folder)
    with override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True):
        AuditSinkSerializer().update(
            ep,
            {
                "oauth_config": {
                    "token_url": "https://login.microsoftonline.com/t/oauth2/v2.0/token",
                    "client_id": "cid2",
                }
            },
        )
    ep.refresh_from_db()
    assert ep.oauth_config["client_id"] == "cid2"
    assert ep.oauth_config["client_secret"] == "csecret"


def test_validate_oauth_requires_token_url_and_client_id():
    from rest_framework import serializers as drf
    from webhooks.serializers import AuditSinkSerializer

    serializer = AuditSinkSerializer()
    with pytest.raises(drf.ValidationError) as exc:
        serializer.validate(
            {
                "transport": WebhookEndpoint.Transport.HTTP,
                "auth_type": WebhookEndpoint.AuthType.OAUTH2_CC,
                "oauth_config": {"scope": "s"},
            }
        )
    message = str(exc.value)
    assert "token_url" in message and "client_id" in message


def test_validate_oauth_config_rejects_non_string_values():
    from rest_framework import serializers as drf
    from webhooks.serializers import AuditSinkSerializer

    with pytest.raises(drf.ValidationError):
        AuditSinkSerializer().validate_oauth_config({"client_id": {"nested": 1}})


@pytest.mark.django_db
@override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=False)
def test_oauth_token_url_must_be_public(root_folder):
    from django.core.exceptions import ValidationError
    from core.net_safety import BlockedRequestError

    # The token endpoint is an outbound request from our server, so it faces the
    # same SSRF guard as the sink URL. Stubbed to keep DNS out of the test.
    def guard(url, **kwargs):
        if "127.0.0.1" in url:
            raise BlockedRequestError("blocked")

    ep = WebhookEndpoint(
        name="siem",
        url="https://siem.example/collector",
        kind=WebhookEndpoint.Kind.AUDIT_SINK,
        transport=WebhookEndpoint.Transport.HTTP,
        auth_type=WebhookEndpoint.AuthType.OAUTH2_CC,
        oauth_config={"token_url": "http://127.0.0.1/token", "client_id": "c"},
        folder=root_folder,
    )
    with patch("webhooks.models.assert_public_url", side_effect=guard):
        with pytest.raises(ValidationError) as exc:
            ep.clean()
    assert "oauth_config" in exc.value.message_dict
