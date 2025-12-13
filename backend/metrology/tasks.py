from datetime import date, timedelta
from huey import crontab
from huey.contrib.djhuey import db_periodic_task

import logging.config
from django.conf import settings
import structlog

logging.config.dictConfig(settings.LOGGING)
logger = structlog.getLogger(__name__)


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
