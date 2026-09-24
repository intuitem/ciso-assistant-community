"""The login throttle is allauth's, but it only works because `CACHES["default"]`
is a database table every gunicorn worker can see. These cover that wiring: the
cache really is the shared table, and the throttle really blocks through it."""

import pytest
from django.core.cache import caches
from django.core.cache.backends.db import BaseDatabaseCache
from django.db import DEFAULT_DB_ALIAS, connections, router

from iam.models import User

LOGIN_URL = "/api/_allauth/app/v1/auth/login"
PASSWORD = "cOrrect-horse-battery-staple-1"

pytestmark = [pytest.mark.django_db, pytest.mark.db_cache]


def _cache_connection():
    cache = caches["default"]
    alias = router.db_for_write(cache.cache_model_class) or DEFAULT_DB_ALIAS
    return cache, connections[alias]


def _rows(connection, table):
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        return cursor.fetchone()[0]


def test_default_cache_is_the_shared_database_table():
    cache, connection = _cache_connection()
    assert isinstance(cache, BaseDatabaseCache)
    assert cache._table == "auth_throttle_cache"

    before = _rows(connection, cache._table)
    cache.set("throttle-probe", 1, 300)
    assert _rows(connection, cache._table) == before + 1
    assert cache.get("throttle-probe") == 1


def test_throttle_counter_survives_a_spray_from_many_other_keys():
    """Django's default MAX_ENTRIES of 300 culls by lowest `cache_key`, not by
    recency, so an attacker spraying from enough IPs used to evict their own
    counter and reset their budget. settings pins MAX_ENTRIES high; this is the
    regression test for that. Do not lower it without re-running this."""
    cache, _ = _cache_connection()
    victim = "aaa-victim-counter"
    cache.set(victim, 5, 300)

    for i in range(800):
        cache.set(f"zzz-spray-{i:04d}", 1, 300)

    assert cache.get(victim) == 5


def test_failed_logins_are_blocked_at_the_configured_limit(client, settings):
    """Five failures per (email, IP) per 300s, so the sixth must be refused even
    though the password is still wrong -- and the counter lives in the table."""
    settings.ACCOUNT_RATE_LIMITS = {"login_failed": "5/300s/key"}
    User.objects.create_user(email="victim@example.invalid", password=PASSWORD)
    cache, connection = _cache_connection()
    before = _rows(connection, cache._table)

    bodies = [
        client.post(
            LOGIN_URL,
            data={"email": "victim@example.invalid", "password": "wrong"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.9",
        ).content.decode()
        for _ in range(6)
    ]

    # Headless answers 400 for both a wrong password and a refusal, so the error
    # code is what tells them apart.
    throttled = ["too_many_login_attempts" in body for body in bodies]
    assert throttled == [False] * 5 + [True], bodies
    assert _rows(connection, cache._table) > before


def test_a_different_ip_is_not_locked_out_by_the_flood(client, settings):
    """The key is scoped to (email, IP) so a flood cannot lock the real user out
    of their own account from somewhere else."""
    settings.ACCOUNT_RATE_LIMITS = {"login_failed": "5/300s/key"}
    User.objects.create_user(email="victim2@example.invalid", password=PASSWORD)

    for _ in range(6):
        client.post(
            LOGIN_URL,
            data={"email": "victim2@example.invalid", "password": "wrong"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.9",
        )

    response = client.post(
        LOGIN_URL,
        data={"email": "victim2@example.invalid", "password": PASSWORD},
        content_type="application/json",
        REMOTE_ADDR="198.51.100.4",
    )
    assert response.status_code != 429


@pytest.mark.django_db(transaction=True)
def test_concurrent_add_lets_exactly_one_caller_win():
    """allauth 65.19.3 fixes a concurrency bypass by taking a lock around every
    rate-limit update, and that lock is `cache.add`. We are still on 65.19.2, so
    nothing takes it yet; this guards the property the bump will depend on. `add`
    has to be a real compare-and-set, which for DatabaseCache means the unique
    constraint on cache_key: the loser's INSERT raises and Django returns False.

    This discriminates on PostgreSQL, where concurrent readers all see an empty
    row and race to INSERT. On SQLite it passes either way, because SQLite
    serialises writers anyway -- a deliberately non-atomic get-then-set was
    measured to produce a single winner there too.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from django.db import connection as default_connection

    cache, _ = _cache_connection()
    cache.delete("contended-lock")

    # Without the barrier the first caller wins before the rest even start, and
    # the assertion would hold on a completely non-atomic `add`.
    workers = 16
    gate = threading.Barrier(workers)

    def contend(_):
        gate.wait()
        try:
            return cache.add("contended-lock", True, 10)
        finally:
            default_connection.close()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        won = list(pool.map(contend, range(workers)))

    assert won.count(True) == 1, won
