from huey import crontab
from huey.contrib.djhuey import db_periodic_task, task

import structlog

logger = structlog.get_logger(__name__)


@task()
def run_kev_sync():
    """On-demand KEV sync triggered from the UI."""
    from sec_intel.feeds import KEVFeed

    try:
        result = KEVFeed().sync()
        logger.info("KEV sync completed (on-demand)", **result)
    except Exception:
        logger.warning("KEV sync failed (on-demand)", exc_info=True)


@task()
def run_euvd_sync():
    """On-demand EUVD sync triggered from the UI."""
    from sec_intel.feeds import EUVDFeed

    try:
        result = EUVDFeed().sync()
        logger.info("EUVD sync completed (on-demand)", **result)
    except Exception:
        logger.warning("EUVD sync failed (on-demand)", exc_info=True)


@task()
def run_cwe_sync():
    """On-demand CWE sync triggered from the UI."""
    from sec_intel.feeds import CWEFeed

    try:
        result = CWEFeed().sync()
        logger.info("CWE sync completed (on-demand)", **result)
    except Exception:
        logger.warning("CWE sync failed (on-demand)", exc_info=True)


@db_periodic_task(crontab(hour="3", minute="0"))
def sync_kev_feed():
    """Daily KEV sync at 03:00. Checks settings first."""
    from sec_intel.feeds import KEVFeed, get_feed_settings

    settings = get_feed_settings()
    if not settings.get("kev_feed_enabled", False):
        return

    try:
        result = KEVFeed().sync()
        logger.info("KEV feed sync completed", **result)
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
