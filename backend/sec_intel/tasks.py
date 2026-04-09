from huey import crontab
from huey.contrib.djhuey import db_periodic_task

import structlog

logger = structlog.get_logger(__name__)


@db_periodic_task(crontab(hour="3", minute="0"))
def sync_kev_feed():
    """Daily KEV sync at 03:00. Checks settings first."""
    from sec_intel.feeds import KEVFeed, get_feed_settings

    settings = get_feed_settings()
    if not settings.get("kev_feed_enabled", False):
        return

    try:
        count = KEVFeed().sync()
        logger.info("KEV feed sync completed", updated_count=count)
    except Exception:
        logger.warning("KEV feed sync failed", exc_info=True)


@db_periodic_task(crontab(hour="3", minute="30"))
def sync_epss_feed():
    """Daily EPSS sync at 03:30. Checks settings first."""
    from sec_intel.feeds import EPSSFeed, get_feed_settings

    settings = get_feed_settings()
    if not settings.get("epss_feed_enabled", False):
        return

    try:
        count = EPSSFeed().sync()
        logger.info("EPSS feed sync completed", updated_count=count)
    except Exception:
        logger.warning("EPSS feed sync failed", exc_info=True)
