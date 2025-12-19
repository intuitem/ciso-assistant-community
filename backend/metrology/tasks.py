from datetime import date, timedelta
from huey import crontab
from huey.contrib.djhuey import db_periodic_task

import logging.config
from django.conf import settings
import structlog

from metrology.models import MetricInstance

logging.config.dictConfig(settings.LOGGING)
logger = structlog.getLogger(__name__)


def _update_stale_status(frequencies: list):
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

    retention_days = get_builtin_metrics_retention_days()
    cutoff_date = date.today() - timedelta(days=retention_days)

    deleted_count, _ = BuiltinMetricSample.objects.filter(date__lt=cutoff_date).delete()

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
