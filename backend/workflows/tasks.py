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
    from .engine import run_instance
    from .models import WorkflowToken

    token = WorkflowToken.objects.filter(
        id=token_id, status=WorkflowToken.Status.RETRYING
    ).first()
    if token is None:
        return
    token.status = WorkflowToken.Status.ACTIVE
    token.save(update_fields=["status", "updated_at"])
    run_instance(token.instance)


@db_periodic_task(crontab(minute="*"))
def process_workflow_schedules():
    from .scheduling import run_due_schedules

    run_due_schedules()


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
