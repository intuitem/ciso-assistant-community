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

- **`setup_cache_table` is a required setup step, and it runs before `migrate`.** `migrate` ends by emitting `post_migrate`, where `core.startup` seeds feature flags and clears their cache, so the table has to exist before `migrate` finishes. `createcachetable` is not called directly: `backend/core/management/commands/setup_cache_table.py` wraps it, asks the router which database the cache belongs to, and is idempotent, so one command is correct whether or not `CACHE_DB_PATH` is set. A missing table is a hard `OperationalError`, which 500s login, not a degraded mode -- and it also makes `core.startup` skip feature-flag seeding, silently, since that block swallows exceptions.
- **Every path that builds a database has to call it.** Container startup (`backend/startup.sh`), the CI workflows under `.github/workflows/`, the test and packaging scripts, and the manual install instructions all run it before `migrate`. `grep -rn 'manage.py migrate'` finds the full set; anything it turns up has to run `setup_cache_table` first. This repetition is the real cost of not using a migration.
- **No migration creates this table, deliberately.** Migrations describe model schema, and the cache table is not a model. The cost of that choice is the repetition described above, and CI breaks loudly when one of those places is missed.
- **`MAX_ENTRIES` must stay high (currently 100000).** Django defaults it to 300 and culls by lowest `cache_key` ordering, not by recency. See Security considerations.
- **The cache backend is process-wide, and that cannot be scoped.** allauth imports the `default` alias directly, so every cache user moves to the database with it. In practice that is the feature-flags cache in `global_settings/utils.py`, which now costs a query per check instead of a memory hit, and in exchange gains cross-worker invalidation it did not have before.
- **Tests pin `CACHES` to `LocMemCache`** in `backend/conftest.py`. This must stay. Under `DatabaseCache` a cache hit is itself a query, which breaks the `django_assert_num_queries(0)` assertions in `global_settings/tests/test_feature_flags.py`, and forces database access on tests that declare none. Tests that need the real thing carry `@pytest.mark.db_cache`, which opts out of that pin; `conftest.py` also runs `setup_cache_table` once against the test database, since `migrate` does not create it there either. See `iam/tests/test_login_throttle_cache.py`.
- **`CACHE_DB_PATH` is only meaningful on SQLite.** PostgreSQL has no single-writer lock to avoid, so pointing the cache at a container-local SQLite file there buys nothing and would shard the throttle per pod. The Helm chart exposes it as `backend.config.cacheDbPath` and suppresses it unless `databaseType` is `sqlite`; the setting is not guarded in `settings.py` itself, so non-Helm deployments must respect that rule themselves.
- When `CACHE_DB_PATH` is set, that file gets WAL, `transaction_mode=IMMEDIATE` and a 120s busy timeout, matching `default`, so lock contention waits rather than surfacing as "database is locked".

## Security considerations

- **Cache culling was a throttle bypass, and is why `MAX_ENTRIES` is pinned.** At Django's default of 300 entries, `DatabaseCache._cull` deletes expired rows and then drops a fraction of what remains ordered by `cache_key`, with no regard for recency. An attacker spraying from enough source IPs pushes the table past the cap and evicts their own counter, resetting their budget under exactly the attack the control exists to stop. This was reproduced before the fix and no longer reproduces at 100000. Never lower this value without re-testing that case.
- **Write-lock contention on SQLite is accepted rather than eliminated** when `CACHE_DB_PATH` is unset. Volume is bounded by the `10/m/ip` cap, which holds regardless of how many usernames an attacker rotates through, and each allowed attempt additionally pays for an Argon2 hash across only 3 workers. Reaching a harmful write rate requires thousands of distinct source IPs, at which point worker saturation is the binding failure, not the writer lock.
- **django-allauth must be updated to 65.19.4 for this control to hold.**
65.19.3 fixes the configured limit being exceeded under enough concurrent requests, and 65.19.4 fixes Unicode collation letting `admin` and `ádmin` authenticate the same account while consuming two different throttle keys. Nothing here blocks the bump: the lock 65.19.3 introduces is `cache.add`, which only works if `add` is a real compare-and-set, and on `DatabaseCache` it is -- the losing `INSERT` violates the primary key on `cache_key` and Django returns `False`, which `iam/tests/test_login_throttle_cache.py` covers.
- **The throttle key stays scoped to `(email, client IP)`** so an attacker cannot lock a legitimate user out of their own account from a different address.
- **Counters are not durable.** A restart clears the cache and resets in-flight throttle state. Accepted: the window is minutes, and an attacker cannot induce restarts.

## Alternatives considered

- **A dedicated `LoginAttempt` model**: a second throttle in front of allauth's, with its own settings and migration. Rejected because it duplicates semantics allauth already implements, still writes to the main database, and leaves allauth's own `10/m/ip` cap per worker, so it fixes less of the defect for more code.
- **Redis or Memcached**: the obvious shared cache, rejected by the single-container, no-broker deployment constraint.
- **A data migration calling `createcachetable`**: would have created the table everywhere `migrate` runs, with no setup step to forget. Rejected because migrations describe model schema and the cache table is not a model; a management command invoked from a migration also fixes the choice of cache backend into migration history, where it cannot be changed.
- **Creating the table from `AppConfig.ready()`**: every worker would race to create it on boot, and normal application startup should not perform DDL.
- **Run a single gunicorn worker**: makes `LocMemCache` correct by removing the sharing problem, at an unacceptable throughput cost.
