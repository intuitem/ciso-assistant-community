# Support both SQLite and PostgreSQL

- Status: Accepted (backfilled 2026-08-05; decision dates from project inception)
- Date: 2026-08-05
- Deciders: founding team (rationale reconstructed, to be reviewed)

## Context

CISO Assistant is distributed as a self-hosted community edition. Many users evaluate or run it as a single container with no operational expertise and no appetite for running a database server. At the same time, production deployments at scale need a real RDBMS with proper concurrency, backups and tooling.

## Decision

We will support both database engines through the Django ORM: SQLite as the zero-configuration default, PostgreSQL when `POSTGRES_NAME` and related environment variables are set (`backend/ciso_assistant/settings.py`). Every feature must work identically on both.

## Consequences

- No raw SQL anywhere in application code.
- No PostgreSQL-specific ORM features: no `django.contrib.postgres` fields (ArrayField, HStoreField), no PG-only lookups (trigram, unaccent), no PG-specific index types in models.
- Migrations must apply cleanly on both engines.
- The default test suite runs on SQLite; changes touching query behavior need a PostgreSQL check before merge.
- Deployment stays a single container by default, which also shapes adjacent choices (e.g. background tasks run on huey without a broker).

## Alternatives considered

- **PostgreSQL only**: simpler codebase, richer ORM surface, but kills the friction-free evaluation path that drives community adoption.
- **SQLite only**: does not hold up under production concurrency and enterprise operational requirements.
