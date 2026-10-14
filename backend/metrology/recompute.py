"""Recomputing metric formulas soon after what they read changes.

A mark (series.mark) records which formulas to recompute and from when; this
module turns marks into work. The first mark queues a recompute job
RECOMPUTE_DELAY_SECONDS later, and marks made while it waits queue nothing
more, so a burst of samples costs one job. The job computes every marked
formula, shallow ones first, and repeats while its own results mark further
formulas, so a chain settles in one job. One job runs at a time. The
fifteen-minute sweep (tasks.compute_due_derived_metrics) stays as a
backstop: it marks the formulas whose interval has passed and asks for a job.

Every metric formula computation goes through the job, a refresh and a new
composition included, so dependency order and the one-job rule hold for all
of them. Dataset formulas keep their own task.
"""

import time

import structlog
from django.core.cache import cache
from huey.contrib.djhuey import HUEY

from .derived import LOCK_TTL_SECONDS, DerivedMetricError, compute_sample
from .series import depth, mark

logger = structlog.get_logger(__name__)

# Long enough to gather a burst of samples into one job. A delayed task
# reaches the queue at the worker's next scheduler pass, so the worker's
# --scheduler-interval adds to it.
RECOMPUTE_DELAY_SECONDS = 2
# "A job is queued". Taken by the web processes that mark and released by
# the worker that runs the job, so it lives in the task queue's storage,
# which every process shares. Its value is when it was taken: one older than
# PENDING_STALE_SECONDS belongs to a job that never ran (a worker killed with
# the job still queued) and is taken over.
PENDING_KEY = "metrology:formula-recompute-pending"
PENDING_STALE_SECONDS = 300
# "A job is running". Only the worker runs jobs, so the cache holds it, as it
# holds the per-instance lock (see derived.LOCK_TTL_SECONDS).
RUNNING_KEY = "metrology:formula-recompute-running"


def request_recompute():
    """Queue a recompute job, unless one is already queued."""
    now = time.time()
    if not HUEY.put_if_empty(PENDING_KEY, now):
        taken = HUEY.get(PENDING_KEY, peek=True)
        if taken is not None and now - taken < PENDING_STALE_SECONDS:
            return
        HUEY.put(PENDING_KEY, now)
    from .tasks import recompute_marked_formulas

    recompute_marked_formulas.schedule(delay=RECOMPUTE_DELAY_SECONDS)


def recompute_soon(instance_ids, moment):
    """Mark these metric formula instances from ``moment`` and queue a job."""
    mark(instance_ids, moment)
    request_recompute()


def run_job():
    """The queued job. The pending flag goes first, so a mark made while the
    job runs queues the next one; a job finding another one running comes
    back later instead of waiting, and the marks wait with it."""
    HUEY.delete(PENDING_KEY)
    if not cache.add(RUNNING_KEY, "1", LOCK_TTL_SECONDS):
        request_recompute()
        return
    try:
        computed = compute_marked_formulas()
    finally:
        cache.delete(RUNNING_KEY)
    if computed:
        logger.info("metric formulas recomputed", instances=computed)


def compute_marked_formulas():
    """Every marked metric formula of an active or stale instance, shallow
    ones first, until none is left: a formula's new values mark the
    formulas reading it, which the next round computes. Each instance runs
    at most once, so one whose computation crashes, and gives its mark back,
    waits for the next job. Returns how many ran."""
    from .models import MetricInstance

    attempted = set()
    depths = {}
    while True:
        marked = [
            instance
            for instance in MetricInstance.objects.filter(
                recompute_from__isnull=False,
                status__in=[
                    MetricInstance.Status.ACTIVE,
                    MetricInstance.Status.STALE,
                ],
            )
            .exclude(id__in=attempted)
            .select_related("metric_definition", "folder")
            if instance.metric_definition.reads_metrics
        ]
        if not marked:
            return len(attempted)
        for instance in marked:
            definition = instance.metric_definition
            if definition.id not in depths:
                depths[definition.id] = depth(definition)
        for instance in sorted(marked, key=lambda i: depths[i.metric_definition_id]):
            attempted.add(instance.id)
            compute_isolated(instance, "metric formula")


def compute_isolated(instance, what):
    """Compute one instance; its failure is logged, never raised, so the
    instances after it still get their turn."""
    try:
        compute_sample(instance, only_if_due=True)
    except DerivedMetricError as e:
        # Recorded on the instance by compute_sample; the log is for operators.
        logger.warning(
            f"{what} computation failed",
            metric_instance_id=str(instance.id),
            error=e.message,
        )
    except Exception:
        logger.exception(
            f"{what} computation crashed",
            computation=what,
            metric_instance_id=str(instance.id),
        )
