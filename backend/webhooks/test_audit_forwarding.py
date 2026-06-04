"""Tests for audit-log → SIEM forwarding (Phase 1: OCSF body + dispatch)."""

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
