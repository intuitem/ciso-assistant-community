"""Engine-owned run context: the variables every run starts with."""

import re
from zoneinfo import ZoneInfo

from django.utils import timezone

# Written by the engine on every run; a graph may not declare them.
RESERVED_VARIABLE_KEYS = frozenset({"now", "today", "payload"})

VARIABLE_KEY_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def run_timezone(trigger_registration=None):
    """A schedule reads its dates in its own timezone, everything else in the
    deployment default. Falls back rather than failing: publish validated it."""
    tz_name = (getattr(trigger_registration, "config", None) or {}).get("timezone")
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except KeyError, ValueError, TypeError:
            pass
    return timezone.get_default_timezone()


def temporal_seeds(trigger_registration=None):
    """{{now}}/{{today}}, resolved once at run start so a retried node compares
    against the same date as the first attempt."""
    moment = timezone.now().astimezone(run_timezone(trigger_registration))
    return {
        "now": moment.replace(microsecond=0).isoformat(),
        "today": moment.date().isoformat(),
    }
