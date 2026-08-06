"""Periodic workflow scheduling (spec D19).

Schedules are DB rows, not huey periodic tasks: huey's periodic registry is
fixed at import time in the consumer, so user CRUD could never reach it. A
single static tick (workflows.tasks.process_workflow_schedules) claims due
rows and enqueues runs. Dueness is `next_run_at <= now`, so occurrences
missed while the consumer was down coalesce into one run on the next tick.
"""

from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from cronsim import CronSim, CronSimError

# Product floor on schedule frequency. Cron granularity is one minute, so at
# this value the check is a no-op, but it stays as the knob to tighten if
# every-minute user workflows ever become a problem.
MIN_INTERVAL = timedelta(minutes=1)
_SAMPLE_SIZE = 13


class CronValidationError(ValueError):
    pass


def validate_cron_expression(expression: str, tz_name: str = "UTC"):
    """Raise CronValidationError if the expression is invalid, never fires,
    or can fire more often than MIN_INTERVAL."""
    now = datetime.now(_zone(tz_name)).replace(second=0, microsecond=0)
    try:
        iterator = CronSim(expression, now)
        occurrences = [next(iterator) for _ in range(_SAMPLE_SIZE)]
    except (CronSimError, StopIteration) as e:
        raise CronValidationError("invalidCronExpression") from e
    deltas = [later - earlier for earlier, later in zip(occurrences, occurrences[1:])]
    if min(deltas) < MIN_INTERVAL:
        raise CronValidationError("cronIntervalTooShort")


def validate_timezone(tz_name: str):
    try:
        _zone(tz_name)
    except (ValueError, KeyError) as e:
        raise CronValidationError("invalidTimezone") from e


def next_occurrence(expression: str, tz_name: str, after: datetime):
    """Next fire time strictly after `after`, as an aware UTC datetime.
    Returns None when the expression is invalid or never fires again."""
    try:
        local = after.astimezone(_zone(tz_name))
        return next(CronSim(expression, local)).astimezone(dt_timezone.utc)
    except CronSimError, StopIteration, ValueError, KeyError:
        return None


def _zone(tz_name: str):
    try:
        return ZoneInfo(tz_name)
    except Exception as e:
        raise KeyError(tz_name) from e


def run_due_schedules(now=None):
    """One scheduler tick. Claims each due schedule registration with an
    optimistic compare-and-swap on next_run_at, so concurrent or replayed
    ticks (huey enqueues periodic tasks from every consumer's scheduler) fire
    at most once per occurrence. Returns the instances that were started."""
    from django.utils import timezone

    from .engine import EngineError, create_instance
    from .models import WorkflowInstance, WorkflowNode, WorkflowTrigger
    from .tasks import run_instance_task

    now = now or timezone.now()
    due = WorkflowTrigger.objects.filter(
        type=WorkflowTrigger.Type.SCHEDULE, enabled=True, next_run_at__lte=now
    ).select_related("workflow")
    started = []
    for registration in due:
        config = registration.config or {}
        claimed = WorkflowTrigger.objects.filter(
            id=registration.id, next_run_at=registration.next_run_at
        ).update(
            next_run_at=next_occurrence(
                config.get("cron_expression", ""), config.get("timezone", "UTC"), now
            ),
            last_run_at=now,
        )
        if not claimed:
            continue
        version = registration.workflow.published_version
        entry = None
        if version is not None:
            entry = version.nodes.filter(
                type=WorkflowNode.Type.TRIGGER, ref=registration.node_ref
            ).first()
        if not registration.workflow.is_active:
            # The CAS claim above already advanced next_run_at, so
            # reactivation resumes on the next occurrence — no catch-up storm.
            result = WorkflowTrigger.Result.SKIPPED_INACTIVE
        elif version is None:
            result = WorkflowTrigger.Result.SKIPPED_UNPUBLISHED
        elif version.run_as is None:
            # Spec D34: no run identity, no automatic execution. next_run_at
            # already advanced by the claim — republishing resumes on the
            # next natural occurrence.
            result = WorkflowTrigger.Result.SKIPPED_NO_IDENTITY
        elif entry is None:
            # A publish raced the claim and removed the node; the row is on
            # its way out (or already gone — update below is then a no-op).
            result = WorkflowTrigger.Result.ERROR
        elif registration.instances.filter(
            status=WorkflowInstance.Status.ACTIVE
        ).exists():
            # concurrencyPolicy: Forbid — an every-minute cron on a slow
            # workflow must not pile up instances.
            result = WorkflowTrigger.Result.SKIPPED_OVERLAP
        else:
            try:
                instance = create_instance(
                    version,
                    trigger=WorkflowInstance.Trigger.SCHEDULED,
                    entry_node=entry,
                    trigger_registration=registration,
                )
            except EngineError:
                result = WorkflowTrigger.Result.ERROR
            else:
                run_instance_task(str(instance.id))
                started.append(instance)
                result = WorkflowTrigger.Result.TRIGGERED
        WorkflowTrigger.objects.filter(id=registration.id).update(last_result=result)
    return started
