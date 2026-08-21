from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task


@db_task()
def run_instance_task(instance_id):
    from .engine import run_instance
    from .models import WorkflowInstance

    instance = WorkflowInstance.objects.filter(id=instance_id).first()
    if instance is not None:
        run_instance(instance)


@db_task()
def retry_token_task(token_id):
    from django.utils import timezone

    from .engine import run_instance
    from .models import WorkflowToken

    # Exclusive claim (same CAS pattern as run_due_schedules): Huey may
    # deliver a task twice, and a read-then-save window would let both
    # deliveries run the instance.
    claimed = WorkflowToken.objects.filter(
        id=token_id, status=WorkflowToken.Status.RETRYING
    ).update(status=WorkflowToken.Status.ACTIVE, updated_at=timezone.now())
    if not claimed:
        return
    token = WorkflowToken.objects.select_related("instance").get(id=token_id)
    run_instance(token.instance)


@db_periodic_task(crontab(minute="*"))
def process_workflow_schedules():
    from .scheduling import run_due_schedules

    run_due_schedules()


@db_periodic_task(crontab(minute="*"))
def reap_timed_out_runs():
    """Terminate runs past their absolute TTL. The inline check in
    _run covers sync + resumed runs; this catches runs parked WAITING on an
    event/subprocess that never resumes — they never re-enter _run on their
    own. Needs the Huey worker running (same as scheduled triggers)."""
    from django.db import transaction

    from .engine import _is_over_ttl, _lock_instance_tree, _timeout_instance
    from .models import WorkflowInstance

    candidates = WorkflowInstance.objects.filter(
        status=WorkflowInstance.Status.ACTIVE,
        version__timeout_seconds__gt=0,
    ).values_list("id", flat=True)
    for instance_id in list(candidates):
        with transaction.atomic():
            # Tree lock (root ancestor first): _timeout_instance abandons
            # children, so this transaction must follow the engine's
            # top-down lock order.
            instance = _lock_instance_tree(instance_id)
            if instance.status == WorkflowInstance.Status.ACTIVE and _is_over_ttl(
                instance
            ):
                _timeout_instance(instance)


@db_task()
def dispatch_bulk_event_task(payload, origin_depth=0):
    """Bulk-write producer counterpart of dispatch_internal_event_task: the
    payload is already built (there is no LogEntry row for a bulk write), so
    it dispatches directly."""
    from .events import dispatch_internal_event

    dispatch_internal_event(
        payload["event_key"],
        payload,
        payload.get("folder_id"),
        origin_depth=origin_depth,
    )


@db_task()
def dispatch_internal_event_task(log_entry_id, origin_depth=0):
    from auditlog.models import LogEntry

    from .events import dispatch_internal_event, payload_from_log_entry

    log_entry = (
        LogEntry.objects.filter(pk=log_entry_id)
        .select_related("content_type", "actor")
        .first()
    )
    if log_entry is None or log_entry.content_type is None:
        return
    payload = payload_from_log_entry(log_entry)
    dispatch_internal_event(
        payload["event_key"],
        payload,
        payload.get("folder_id"),
        origin_depth=origin_depth,
    )
