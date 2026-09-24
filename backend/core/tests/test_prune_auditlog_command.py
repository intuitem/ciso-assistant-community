"""Tests for the `prune_auditlog` management command.

The command keeps two independent count quotas: regular business audit
(AUDITLOG_MAX_RECORDS) and security events such as failed logins
(AUDITLOG_SECURITY_MAX_RECORDS, actions in AUDITLOG_SECURITY_ACTIONS). The
partition exists so a flood of security entries can only evict older security
entries, never the business audit trail.
"""

from datetime import timedelta

import pytest
from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

User = get_user_model()

CREATE = 0  # LogEntry.Action.CREATE (business)
LOGIN_FAILED = 4  # enterprise LogEntryAction.LOGIN_FAILED (security)


def _entries(action, count, base_offset_seconds):
    # The test DB is seeded with library-load LogEntry rows; callers reset the
    # table first so quotas apply only to the rows under test.
    ct = ContentType.objects.get_for_model(User)
    now = timezone.now()
    LogEntry.objects.bulk_create(
        LogEntry(
            content_type=ct,
            object_pk="0",
            object_repr="x",
            action=action,
            timestamp=now - timedelta(seconds=base_offset_seconds - i),
        )
        for i in range(count)
    )


@pytest.mark.django_db
@override_settings(
    AUDITLOG_MAX_RECORDS=100,
    AUDITLOG_SECURITY_MAX_RECORDS=10,
    AUDITLOG_SECURITY_ACTIONS=[LOGIN_FAILED],
)
def test_security_flood_does_not_evict_business_audit():
    LogEntry.objects.all().delete()
    # Business rows are the OLDEST; under a single shared quota they would be
    # deleted first. Partitioned, they sit under their own quota and survive.
    _entries(CREATE, 4, base_offset_seconds=10_000)
    _entries(LOGIN_FAILED, 50, base_offset_seconds=5_000)

    call_command("prune_auditlog")

    assert LogEntry.objects.filter(action=CREATE).count() == 4
    assert LogEntry.objects.filter(action=LOGIN_FAILED).count() == 10


@pytest.mark.django_db
@override_settings(
    AUDITLOG_MAX_RECORDS=10,
    AUDITLOG_SECURITY_MAX_RECORDS=10,
    AUDITLOG_SECURITY_ACTIONS=[LOGIN_FAILED],
)
def test_regular_quota_still_prunes_oldest_business():
    LogEntry.objects.all().delete()
    _entries(CREATE, 15, base_offset_seconds=5_000)

    call_command("prune_auditlog")

    assert LogEntry.objects.filter(action=CREATE).count() == 10


@pytest.mark.django_db
@override_settings(AUDITLOG_MAX_RECORDS=10, AUDITLOG_SECURITY_ACTIONS=[])
def test_no_security_actions_prunes_everything_as_regular():
    LogEntry.objects.all().delete()
    _entries(CREATE, 8, base_offset_seconds=5_000)
    _entries(LOGIN_FAILED, 8, base_offset_seconds=3_000)

    call_command("prune_auditlog")

    # With no security partition all 16 rows share the regular quota of 10.
    assert LogEntry.objects.count() == 10
