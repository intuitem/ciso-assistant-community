from datetime import datetime, timedelta

# A license stays valid through the end of its expiration day, so a one-day
# grace period is added to the configured expiration date. Single source of
# truth shared by license enforcement (permissions) and status reporting (views).
LICENSE_GRACE_PERIOD = timedelta(days=1)


def effective_expiration(expiration_date: datetime) -> datetime:
    """Return the moment the license actually stops being valid."""
    return expiration_date + LICENSE_GRACE_PERIOD
