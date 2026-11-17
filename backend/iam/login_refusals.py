"""Logins refused by the rate limits are logged, squashed, per IP address and
per email: a line at the 2nd, 4th, 8th... refusal, and at least every 5 minutes
while refusals go on. A first refusal is not logged: a spray of emails from one
IP address would make one line per email, and many IP addresses trying one
email one line per address. Counts restart 1 hour after a first refusal."""

import hashlib

import structlog
from django.core.cache import cache

from core.custom_middleware import resolve_client_ip

logger = structlog.get_logger(__name__)

COUNT_SECONDS = 60 * 60
RECAP_SECONDS = 5 * 60


def record_refused_login(request, credentials):
    username = credentials.get("email") or credentials.get("username")
    for field, value in (
        ("remote_addr", resolve_client_ip(request)),
        ("username", username),
    ):
        if value:
            _count_refusal(field, value)


def _count_refusal(field, value):
    key = f"login-refusals:{field}:{hashlib.sha256(value.encode()).hexdigest()}"
    if cache.add(key, 1, COUNT_SECONDS):
        return
    try:
        count = cache.incr(key)
    except ValueError:  # the count expired in between
        return
    if not count:  # the cache is unavailable
        return

    power_of_two = (count & (count - 1)) == 0
    recap_due = cache.add(f"{key}:recap", True, RECAP_SECONDS)
    if not (power_of_two or recap_due):
        return
    if not recap_due:
        cache.set(f"{key}:recap", True, RECAP_SECONDS)
    logger.warning("Logins refused by rate limit", **{field: value}, refused=count)
