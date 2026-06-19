"""Audit-log forwarding producer.

A single post_save receiver on auditlog's LogEntry is the broadest hook: it
fires for every created entry, including m2m changes (which bypass auditlog's
own post_log signal). We defer to a Huey task on commit so the task reads the
committed, enriched row — sidestepping in-memory staleness and signal ordering.
"""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from auditlog.models import LogEntry
from global_settings.utils import ff_is_enabled

from .tasks import dispatch_audit_event


@receiver(post_save, sender=LogEntry)
def forward_audit_log_entry(sender, instance, created, **kwargs):
    if not created or instance.action == LogEntry.Action.ACCESS:
        return
    if not ff_is_enabled("audit_log_forwarding"):
        return
    pk = instance.pk
    transaction.on_commit(lambda: dispatch_audit_event.schedule(args=(pk,), delay=1))
