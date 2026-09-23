# Back the login throttle with a shared database cache

- Status: Accepted (2026-09-23)
- Deciders: @tchoumi313 @ab-smith

## Context

django-allauth already throttles failed logins through `django.core.cache`, configured as `ACCOUNT_RATE_LIMITS = {"login_failed": "10/m/ip,5/300s/key"}`, with `AccountAdapter._get_login_attempts_cache_key` scoping the key to `(email, client IP)`. The backend set no `CACHES`, so Django fell back to `LocMemCache`, which is per process.

Production runs gunicorn with 3 workers, so each worker held its own counter and the effective limit was three times the configured one. A flood against a real 3-worker instance let 25 and 45 attempts through before blocking, instead of 5.

The fix had to work without Redis, since the product ships as a single self-hosted container, and had to behave identically on SQLite and PostgreSQL per [dual-database-support](dual-database-support.md).

## Decision

We will point `CACHES["default"]` at `django.core.cache.backends.db.DatabaseCache` on the table `auth_throttle_cache`, so allauth's existing counters become shared across workers without introducing a throttle of our own. `CACHE_DB_PATH` optionally routes that table to a dedicated SQLite file via `ciso_assistant.routers.CacheDBRouter`, for deployments that want throttle writes off the main database's writer lock.

## Consequences

- **`createcachetable` is a required setup step.** `startup.sh` runs it after `migrate` for Docker and Helm. Local development must run it by hand; it is documented in `README.md` and `product-docs/contributing/code.md`. A missing table is a hard `OperationalError`, which 500s both login and feature flags, not a degraded mode.
- **`MAX_ENTRIES` must stay high (currently 100000).** Django defaults it to 300 and culls by lowest `cache_key` ordering, not by recency. See Security considerations.
- **The cache backend is process-wide, and that cannot be scoped.** allauth imports the `default` alias directly, so every cache user moves to the database with it. In practice that is the feature-flags cache in `global_settings/utils.py`, which now costs a query per check instead of a memory hit, and in exchange gains cross-worker invalidation it did not have before.
- **Tests pin `CACHES` to `LocMemCache`** in `backend/conftest.py`. This must stay. Under `DatabaseCache` a cache hit is itself a query, which breaks the `django_assert_num_queries(0)` assertions in `global_settings/tests/test_feature_flags.py`, and forces database access on tests that declare none.
- **`CACHE_DB_PATH` is only meaningful on SQLite.** PostgreSQL has no single-writer lock to avoid, so setting it there buys nothing and adds a needless SQLite dependency. It is not guarded in code.
- When `CACHE_DB_PATH` is set, that file gets WAL and a 60s busy timeout so lock contention surfaces as a database error rather than a killed worker.

## Security considerations

- **Cache culling was a throttle bypass, and is why `MAX_ENTRIES` is pinned.** At Django's default of 300 entries, `DatabaseCache._cull` deletes expired rows and then drops a fraction of what remains ordered by `cache_key`, with no regard for recency. An attacker spraying from enough source IPs pushes the table past the cap and evicts their own counter, resetting their budget under exactly the attack the control exists to stop. This was reproduced before the fix and no longer reproduces at 100000. Never lower this value without re-testing that case.
- **Write-lock contention on SQLite is accepted rather than eliminated** when `CACHE_DB_PATH` is unset. Volume is bounded by the `10/m/ip` cap, which holds regardless of how many usernames an attacker rotates through, and each allowed attempt additionally pays for an Argon2 hash across only 3 workers. Reaching a harmful write rate requires thousands of distinct source IPs, at which point worker saturation is the binding failure, not the writer lock.
- **The throttle key stays scoped to `(email, client IP)`** so an attacker cannot lock a legitimate user out of their own account from a different address.
- **Counters are not durable.** A restart clears the cache and resets in-flight throttle state. Accepted: the window is minutes, and an attacker cannot induce restarts.

## Alternatives considered

- **A dedicated `LoginAttempt` model**: a second throttle in front of allauth's, with its own settings and migration. Rejected because it duplicates semantics allauth already implements, still writes to the main database, and leaves allauth's own `10/m/ip` cap per worker, so it fixes less of the defect for more code.
- **Redis or Memcached**: the obvious shared cache, rejected by the single-container, no-broker deployment constraint.
- **Run a single gunicorn worker**: makes `LocMemCache` correct by removing the sharing problem, at an unacceptable throughput cost.
