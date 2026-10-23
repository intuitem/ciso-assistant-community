"""License part of the instance status (settings.INSTANCE_STATUS_EXTENSIONS):
the seats/editors/expiration fields of the `status` command line and their
Prometheus gauges."""

from datetime import date, datetime, timezone

from django.conf import settings

from core.instance_metrics import get_or_create_gauge

from .license import get_editors

nb_seats_gauge = get_or_create_gauge(
    "ciso_assistant_nb_seats",
    "Number of seats in the CISO Assistant instance",
)
nb_editors_gauge = get_or_create_gauge(
    "ciso_assistant_nb_editors",
    "Number of editors in the CISO Assistant instance",
)
expiration_gauge = get_or_create_gauge(
    "ciso_assistant_license_expiration",
    "Expiration date of the CISO Assistant license",
)


def status_fields() -> list[tuple[str, object]]:
    return [
        ("seats", settings.LICENSE_SEATS),
        ("editors", len(get_editors())),
        ("expiration", settings.LICENSE_EXPIRATION),
    ]


def update_metrics() -> None:
    nb_seats_gauge.set(settings.LICENSE_SEATS)
    nb_editors_gauge.set(len(get_editors()))
    # Prometheus only has float64 gauges, so the expiration date becomes a UTC
    # timestamp, and -1 for unset/invalid dates.
    try:
        expiration_date = date.fromisoformat(str(settings.LICENSE_EXPIRATION))
        expiration_ts = int(
            datetime(
                expiration_date.year,
                expiration_date.month,
                expiration_date.day,
                tzinfo=timezone.utc,
            ).timestamp()
        )
    except ValueError, AttributeError, TypeError:
        expiration_ts = -1
    expiration_gauge.set(expiration_ts)
