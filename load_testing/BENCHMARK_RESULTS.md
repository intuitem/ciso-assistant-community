# SQLite vs PostgreSQL load-test results

Date: 2026-07-09
Branch: `portals_attachment_fix_0907`
Target: validate a production-like 50-concurrent-user workload for CISO Assistant.

## Objective

Benchmark CISO Assistant with the same workload against:

1. SQLite
2. PostgreSQL 17

The goal is to understand whether the application can handle **50 concurrent users** comfortably in a production-style deployment and to identify practical infrastructure settings.

## Test topology

Both database variants used the same application topology:

```text
Locust -> Caddy -> SvelteKit frontend / Django API -> database
```

Primary benchmark traffic targeted authenticated Django API endpoints through Caddy. This avoids browser noise while still approximating SvelteKit SSR/API activity.

### Runtime settings

| Setting | 50-user target runs | 100-user headroom runs |
|---|---:|---:|
| Gunicorn workers | `3` | `3` |
| Gunicorn worker class | sync | sync |
| Caddy | enabled, reverse proxy on port `8080` | enabled, reverse proxy on port `8080` |
| Huey | enabled, `2` workers | enabled, `2` workers |
| Users | `50` | `100` |
| Compliance assessments | `50` | `100` |
| Requirement assessments | `5000` | `10000` |
| Duration | `5m` | `10m` |
| Spawn rate | `10 users/s` | `10 users/s` |
| Writes | enabled | enabled |

## Dataset

The benchmark used synthetic load-test data created by:

```bash
load_testing/scripts/create_load_tokens.py
load_testing/scripts/seed_compliance_workload.py
```

The 50-user seed created:

- 50 load-test users with Knox tokens
- 1 load-test domain
- 1 synthetic framework if no loaded framework was available
- 50 compliance assessments
- 5000 associated requirement assessments

The 100-user headroom seed used the same shape scaled to 100 users, 100 compliance assessments, and 10000 requirement assessments.

## Workload model

Locust simulated authenticated users performing a mixed workload:

- list compliance assessments
- open compliance assessment details
- list requirement assessments
- open requirement assessment details
- search/filter table-like endpoints
- dashboard-like endpoints
- update requirement assessments

The realistic write path was:

```http
PATCH /api/requirement-assessments/:id/
```

Each update flips or changes:

- `result`
- `status`
- `observation`
- `extended_result = null`

This approximates many users updating audit items concurrently.

## Commands used for initial 50-user comparison

### SQLite

```bash
GUNICORN_WORKERS=3 docker compose -f load_testing/docker-compose.sqlite.yml up -d --build backend frontend caddy huey qdrant

docker compose -f load_testing/docker-compose.sqlite.yml exec backend \
  python /code/load_testing/scripts/create_load_tokens.py --users 50 --superusers --fresh-tokens \
  --out /code/load_testing/users.csv

docker compose -f load_testing/docker-compose.sqlite.yml exec backend \
  python /code/load_testing/scripts/seed_compliance_workload.py --assessments 50 --fresh \
  --out /code/load_testing/workload.json

ENABLE_WRITES=true docker compose -f load_testing/docker-compose.sqlite.yml run --rm locust \
  -f /mnt/locust/locustfile.py \
  --host http://caddy:8080 \
  --headless -u 50 -r 10 -t 5m \
  --csv /mnt/locust/results/sqlite_50u_5m
```

### PostgreSQL

```bash
GUNICORN_WORKERS=3 docker compose -f load_testing/docker-compose.postgres.yml up -d --build postgres backend frontend caddy huey qdrant

docker compose -f load_testing/docker-compose.postgres.yml exec backend \
  python /code/load_testing/scripts/create_load_tokens.py --users 50 --superusers --fresh-tokens \
  --out /code/load_testing/users.csv

docker compose -f load_testing/docker-compose.postgres.yml exec backend \
  python /code/load_testing/scripts/seed_compliance_workload.py --assessments 50 --fresh \
  --out /code/load_testing/workload.json

ENABLE_WRITES=true docker compose -f load_testing/docker-compose.postgres.yml run --rm locust \
  -f /mnt/locust/locustfile.py \
  --host http://caddy:8080 \
  --headless -u 50 -r 10 -t 5m \
  --csv /mnt/locust/results/postgres_50u_5m
```

## Main results

### Aggregate results

| Metric | SQLite 50u / 50 CA / 5m | PostgreSQL 50u / 50 CA / 5m | SQLite 100u / 100 CA / 10m | PostgreSQL 100u / 100 CA / 10m, 3 workers | PostgreSQL 100u / 100 CA / 10m, 5 workers |
|---|---:|---:|---:|---:|---:|
| Requests | `6286` | `6329` | `23782` | `24174` | `24234` |
| Failures | `0` | `0` | `2` | `0` | `0` |
| Failure rate | `0.00%` | `0.00%` | `0.01%` | `0.00%` | `0.00%` |
| Requests/s | `21.03` | `21.17` | `39.65` | `40.36` | `40.47` |
| Median response time | `39 ms` | `22 ms` | `66 ms` | `39 ms` | `43 ms` |
| Average response time | `65 ms` | `40 ms` | `113 ms` | `61 ms` | `71 ms` |
| p95 response time | `260 ms` | `120 ms` | `420 ms` | `170 ms` | `200 ms` |
| p99 response time | `500 ms` | `390 ms` | `1300 ms` | `630 ms` | `700 ms` |
| Max response time | `698 ms` | `2269 ms` | `3525 ms` | `1060 ms` | `2359 ms` |

### Requirement-assessment update results

Endpoint:

```http
PATCH /api/requirement-assessments/:id/
```

| Metric | SQLite 50u / 50 CA / 5m | PostgreSQL 50u / 50 CA / 5m | SQLite 100u / 100 CA / 10m | PostgreSQL 100u / 100 CA / 10m, 3 workers | PostgreSQL 100u / 100 CA / 10m, 5 workers |
|---|---:|---:|---:|---:|---:|
| Requests | `1375` | `1367` | `5443` | `5594` | `5591` |
| Failures | `0` | `0` | `2` | `0` | `0` |
| Median response time | `61 ms` | `44 ms` | `94 ms` | `70 ms` | `71 ms` |
| Average response time | `67 ms` | `50 ms` | `118 ms` | `84 ms` | `86 ms` |
| p95 response time | `100 ms` | `76 ms` | `190 ms` | `130 ms` | `140 ms` |
| p99 response time | `190 ms` | `94 ms` | `610 ms` | `200 ms` | `210 ms` |
| Max response time | `428 ms` | `735 ms` | `2565 ms` | `982 ms` | `984 ms` |

### Smoke test result

Before the 50-user run, a smaller SQLite smoke test was executed:

| Metric | Value |
|---|---:|
| Users | `5` |
| Duration | `2m` |
| Requests | `280` |
| Failures | `0` |
| Aggregate median | `36 ms` |
| Aggregate average | `37 ms` |
| Max response time | `167 ms` |
| PATCH average | `55 ms` |

## Log findings

No relevant backend errors were observed in either 50-user run.

Checked for:

- `database is locked`
- `error`
- `exception`
- `traceback`
- `timeout`
- `deadlock`
- worker failures

SQLite had no `database is locked` errors during the 5-minute run.

The PostgreSQL 100-user / 100-compliance-assessment / 10-minute runs with 3 and 5 Gunicorn workers also had no relevant backend or PostgreSQL errors.

The SQLite 100-user / 100-compliance-assessment / 10-minute run did not show `database is locked`, but it did produce 2 `502 Bad Gateway` failures on `PATCH /api/requirement-assessments/:id/`. Backend logs showed two Gunicorn workers receiving `SIGBUS` and being restarted around the failure window.

## Interpretation

Both databases handled the short 50-user mixed workload without failures. PostgreSQL also handled the larger 100-user / 100-compliance-assessment / 10-minute run without failures. SQLite completed the same 100-user run, but with two write-path 502s and materially worse tail latency.

PostgreSQL was clearly better for normal latency in the 50-user comparison:

- aggregate median improved from `39 ms` to `22 ms`
- aggregate average improved from `65 ms` to `40 ms`
- aggregate p95 improved from `260 ms` to `120 ms`
- requirement-assessment update p99 improved from `190 ms` to `94 ms`

SQLite performed surprisingly well for this short test, but this does not prove it is the right production choice for 50 concurrent users. SQLite's concurrency risks usually appear under longer sustained write pressure, heavier background jobs, imports, uploads, or lock-heavy transactions.

PostgreSQL is still the safer recommendation for a 50-concurrent-user production target. The 100-user comparison strengthens that recommendation: PostgreSQL had no failures and lower tail latency, while SQLite showed worker instability and a small number of failed write requests.

In the first Gunicorn worker-count comparison, `GUNICORN_WORKERS=5` did not improve the 100-user PostgreSQL result over `GUNICORN_WORKERS=3`; aggregate p95/p99 and PATCH p95/p99 were slightly worse. Treat 3 workers as the current baseline unless longer tests show a different trend.

## Caveats

1. The main SQLite/PostgreSQL target comparison was only `5m`; the headroom comparison was `10m`. A production decision should include longer `20–30m` runs and ideally a `1–2h` soak.
2. Users were superusers. This is acceptable for DB/backend concurrency, but role-scoped auditor/respondent users should be added later.
3. The dataset used a synthetic framework. A real large framework may have different serializer/query behavior.
4. The workload targeted API endpoints, not browser rendering. This is intentional for DB comparison, but SSR/browser checks should be added separately.
5. PostgreSQL had a few high outliers, especially on prime/startup-like requests. These did not cause failures but should be monitored in longer runs.
6. SQLite's 100-user failures were `502` responses correlated with Gunicorn worker `SIGBUS`, not explicit `database is locked` exceptions.

## Recommended next tests

| Test | Purpose |
|---|---|
| `50 users / 30m` SQLite + PostgreSQL | Confirm steady-state behavior |
| `50 users / 2h` PostgreSQL | Soak test for production target |
| `100 users / 30m` PostgreSQL | Longer headroom test after the successful 10m run |
| `50 users / 30m` with `GUNICORN_WORKERS=5` | Tune Gunicorn worker count |
| Role-scoped users | More realistic IAM/RBAC behavior |
| Real framework dataset | More representative assessment structure |
| SSR/browser smoke test | Validate SvelteKit/Caddy/frontend path |

## Initial infrastructure guidance

For a 50-concurrent-user production target:

- prefer PostgreSQL over SQLite
- start with `GUNICORN_WORKERS=3` or `5`
- keep Caddy in front of both frontend and backend
- monitor backend p95/p99 latency and worker timeouts
- monitor PostgreSQL active connections and slow queries
- consider longer soak tests before final sizing

The current short benchmark suggests the app can handle the target shape comfortably with PostgreSQL and likely has enough headroom for further tuning.
