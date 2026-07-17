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
    except (CronSimError, StopIteration, ValueError, KeyError):
        return None


def _zone(tz_name: str):
    try:
        return ZoneInfo(tz_name)
    except Exception as e:
        raise KeyError(tz_name) from e


def run_due_schedules(now=None):
    """One scheduler tick. Claims each due schedule with an optimistic
    compare-and-swap on next_run_at, so concurrent or replayed ticks (huey
    enqueues periodic tasks from every consumer's scheduler) fire at most
    once per occurrence. Returns the instances that were started."""
    from django.utils import timezone

    from .engine import EngineError, create_instance
    from .models import WorkflowInstance, WorkflowSchedule
    from .tasks import run_instance_task

    now = now or timezone.now()
    due = WorkflowSchedule.objects.filter(
        enabled=True, next_run_at__lte=now
    ).select_related("workflow")
    started = []
    for schedule in due:
        claimed = WorkflowSchedule.objects.filter(
            id=schedule.id, next_run_at=schedule.next_run_at
        ).update(
            next_run_at=next_occurrence(
                schedule.cron_expression, schedule.timezone, now
            ),
            last_run_at=now,
        )
        if not claimed:
            continue
        version = schedule.workflow.published_version
        if version is None:
            result = WorkflowSchedule.Result.SKIPPED_UNPUBLISHED
        elif schedule.instances.filter(status=WorkflowInstance.Status.ACTIVE).exists():
            # concurrencyPolicy: Forbid — an every-minute cron on a slow
            # workflow must not pile up instances.
            result = WorkflowSchedule.Result.SKIPPED_OVERLAP
        else:
            try:
                instance = create_instance(
                    version,
                    trigger=WorkflowInstance.Trigger.SCHEDULED,
                    schedule=schedule,
                )
            except EngineError:
                result = WorkflowSchedule.Result.ERROR
            else:
                run_instance_task(str(instance.id))
                started.append(instance)
                result = WorkflowSchedule.Result.TRIGGERED
        WorkflowSchedule.objects.filter(id=schedule.id).update(last_result=result)
    return started
