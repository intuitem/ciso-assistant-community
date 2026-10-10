from datetime import date, timedelta
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task

import logging.config
from django.conf import settings
from django.db import DatabaseError
import structlog

from metrology.models import MetricInstance

logging.config.dictConfig(settings.LOGGING)
logger = structlog.getLogger(__name__)


def _update_stale_status(frequencies: list):
    try:
        active_instances = MetricInstance.objects.filter(
            status=MetricInstance.Status.ACTIVE,
            collection_frequency__in=frequencies,
        )
        stale_count = 0
        for instance in active_instances:
            if instance.is_stale():
                instance.status = MetricInstance.Status.STALE
                instance.save(update_fields=["status", "updated_at"])
                stale_count += 1

        stale_instances = MetricInstance.objects.filter(
            status=MetricInstance.Status.STALE,
            collection_frequency__in=frequencies,
        )
        reactivated_count = 0
        for instance in stale_instances:
            if not instance.is_stale():
                instance.status = MetricInstance.Status.ACTIVE
                instance.save(update_fields=["status", "updated_at"])
                reactivated_count += 1

        if stale_count > 0 or reactivated_count > 0:
            logger.info(
                f"Stale check for {frequencies}: {stale_count} marked stale, {reactivated_count} reactivated"
            )
    except DatabaseError:
        logger.warning("Metrology tables do not exist yet — skipping stale check")


@db_periodic_task(crontab(minute="*/15"))
def check_realtime_metric_staleness():
    _update_stale_status([MetricInstance.Frequency.REALTIME])


@db_periodic_task(crontab(minute="5"))
def check_hourly_metric_staleness():
    _update_stale_status([MetricInstance.Frequency.HOURLY])


@db_periodic_task(crontab(hour="4", minute="0"))
def check_daily_and_longer_metric_staleness():
    _update_stale_status(
        [
            MetricInstance.Frequency.DAILY,
            MetricInstance.Frequency.WEEKLY,
            MetricInstance.Frequency.MONTHLY,
            MetricInstance.Frequency.QUARTERLY,
            MetricInstance.Frequency.YEARLY,
        ]
    )


@db_periodic_task(crontab(hour="3", minute="45"))
def cleanup_old_builtin_metric_samples():
    """
    Clean up BuiltinMetricSample records older than the configured retention period.
    Runs daily at 3:45 AM.
    """
    from metrology.models import BuiltinMetricSample, get_builtin_metrics_retention_days

    try:
        retention_days = get_builtin_metrics_retention_days()
        cutoff_date = date.today() - timedelta(days=retention_days)

        deleted_count, _ = BuiltinMetricSample.objects.filter(
            date__lt=cutoff_date
        ).delete()

        if deleted_count > 0:
            logger.info(
                f"Cleaned up {deleted_count} builtin metric samples older than {cutoff_date} "
                f"(retention: {retention_days} days)"
            )
        else:
            logger.debug(
                f"No builtin metric samples older than {cutoff_date} to clean up "
                f"(retention: {retention_days} days)"
            )
    except DatabaseError:
        logger.warning(
            "Metrology tables do not exist yet — skipping builtin metric sample cleanup"
        )


# ---------- derived metrics ----------


@db_task()
def compute_derived_metric_task(instance_id, only_if_due=False, full=False):
    """One instance, by id: the manual refresh and the sweep both land here.
    The sweep passes ``only_if_due`` so a duplicate it queued while the
    queue lagged finds the instance already computed and writes nothing.
    ``full`` recomputes a metric formula's whole series."""
    from metrology.derived import DerivedMetricError, compute_sample

    instance = (
        MetricInstance.objects.select_related("metric_definition", "folder")
        .filter(id=instance_id)
        .first()
    )
    if instance is None:
        return
    try:
        compute_sample(instance, only_if_due=only_if_due, full=full)
    except DerivedMetricError as e:
        # Recorded on the instance by compute_sample; the log is for operators.
        logger.warning(
            "derived metric computation failed",
            metric_instance_id=str(instance.id),
            error=e.message,
        )


@db_periodic_task(crontab(minute="*/15"))  # derived.SWEEP_INTERVAL
def compute_due_derived_metrics():
    """The sweep: every derived instance past its collection interval, and
    every metric formula an input marked. Metric formulas run here, in
    dependency order, so one reading another reads it fresh. Dataset
    formulas are queued, each on its own, except those a due metric formula
    reads: they run here first, ahead of it, or the formula would read the
    previous tick's value and catch up one sweep later."""
    from metrology.derived import DerivedMetricError, compute_sample, due_instances
    from metrology.series import depth, input_closure

    try:
        due = due_instances()
    except DatabaseError:
        logger.warning("Metrology tables do not exist yet — skipping derived metrics")
        return
    series = [i for i in due if i.metric_definition.reads_metrics]
    datasets = [i for i in due if not i.metric_definition.reads_metrics]
    read_by_series = input_closure(
        {i.metric_definition_id: i.metric_definition for i in series}.values()
    )

    def run(instance, what):
        try:
            compute_sample(instance, only_if_due=True)
        except DerivedMetricError as e:
            logger.warning(
                f"{what} computation failed",
                metric_instance_id=str(instance.id),
                error=e.message,
            )

    for instance in datasets:
        if instance.metric_definition_id in read_by_series:
            run(instance, "derived metric")
        else:
            compute_derived_metric_task(str(instance.id), only_if_due=True)
    depths = {}
    for instance in series:
        definition = instance.metric_definition
        if definition.id not in depths:
            depths[definition.id] = depth(definition)
    for instance in sorted(series, key=lambda i: depths[i.metric_definition_id]):
        run(instance, "metric formula")
    if due:
        logger.info("derived metrics sweep", due=len(due), formulas=len(series))


@db_periodic_task(crontab(hour="3", minute="30"))
def downsample_derived_metric_samples():
    """Older than a week, one derived sample per instance per day."""
    from metrology.derived import downsample_derived_samples

    try:
        deleted = downsample_derived_samples()
    except DatabaseError:
        logger.warning("Metrology tables do not exist yet — skipping downsampling")
        return
    if deleted:
        logger.info("derived metric samples downsampled", deleted=deleted)
