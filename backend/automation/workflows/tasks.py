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


@db_task()
def send_email_task(token_id, subject, body, recipients):
    """Deliver a send_email action's mail and hand the token back to the
    engine. Runs outside any engine transaction so SMTP I/O never blocks the
    instance-tree locks. Best-effort across recipients (one dead address must
    not starve the rest); any failure fails the node so the per-node retry
    policy applies — a retry re-sends to every recipient, including the ones
    already served, accepted over losing the failed ones."""
    import structlog
    from django.conf import settings
    from django.core.mail import get_connection

    from core.tasks import send_email_now

    from .engine import complete_deferred_action, fail_deferred_action
    from .models import WorkflowToken

    logger = structlog.get_logger(__name__)

    token = (
        WorkflowToken.objects.select_related("instance")
        .filter(id=token_id, status=WorkflowToken.Status.WAITING)
        .first()
    )
    if token is None:
        # Duplicate huey delivery, or an operator/reaper moved the token
        # meanwhile. complete/fail re-check WAITING under the tree lock, so
        # this unlocked pre-check only exists to avoid sending mail twice.
        return

    sent, failed = [], []
    ssl_context = getattr(settings, "EMAIL_SSL_CONTEXT", None)
    try:
        # One connection for the whole batch (not one handshake per
        # recipient); individual messages so recipients don't see each other.
        with get_connection(ssl_context=ssl_context) as connection:
            for email in recipients:
                try:
                    send_email_now(subject, body, email, connection=connection)
                    sent.append(email)
                except Exception as e:
                    # Raw exception text stays out of the run log (it can
                    # carry SMTP server internals); detail goes to the
                    # server log.
                    logger.error(
                        "send_email action delivery failure",
                        recipient=email,
                        instance_id=str(token.instance_id),
                        error=str(e),
                    )
                    failed.append(email)
    except Exception as e:
        # The connection itself failed to open or close; recipients not
        # already attempted never got their mail.
        logger.error(
            "send_email action connection failure",
            instance_id=str(token.instance_id),
            error=str(e),
        )
        failed += [r for r in recipients if r not in sent and r not in failed]

    if failed:
        fail_deferred_action(
            token,
            f"send_email: delivery failed for {', '.join(failed)}"
            f" ({len(sent)} of {len(recipients)} sent)",
        )
    else:
        complete_deferred_action(token, {"recipients": recipients, "subject": subject})


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
