# Load testing CISO Assistant: SQLite vs PostgreSQL

Goal: validate whether a production-like deployment (`gunicorn` backend + SvelteKit frontend + Caddy reverse proxy) handles **50 concurrent users comfortably**, compare SQLite vs PostgreSQL under the same workload, and probe 100-user headroom.

This lab intentionally ignores the older ToxiProxy latency setup. It focuses on app/database concurrency.

## What this starts with

- `docker-compose.sqlite.yml` — app stack using SQLite.
- `docker-compose.postgres.yml` — same app stack using PostgreSQL 17.
- `locust/locustfile.py` — authenticated API workload that runs through Caddy.
- `scripts/create_load_tokens.py` — creates load-test users and Knox/PAT tokens.
- `users.example.csv` — token CSV format.

The first workload is **authenticated API traffic**. This is deliberate: SvelteKit SSR ultimately calls the backend API, and API tests make the SQLite/PostgreSQL difference easier to isolate. Browser/SSR page testing can be added later as a smaller complementary scenario.

## Success criteria proposal

For 50 concurrent users, call the run comfortable if all are true during a 15–30 minute steady-state test:

- p95 latency for core API endpoints stays below ~500–800 ms.
- p99 latency stays below ~2 s.
- error rate is below 0.1%.
- no SQLite `database is locked` storm / PostgreSQL lock pile-up.
- backend CPU and memory are stable.
- no sustained Gunicorn worker timeout/restart.

Adjust thresholds if you have explicit product SLOs.

## Quick start: SQLite

From repo root:

```bash
# 1. Start stack
GUNICORN_WORKERS=3 docker compose -f load_testing/docker-compose.sqlite.yml up -d --build backend frontend caddy huey qdrant

# 2. Create 50 test users/tokens in the SQLite DB
# Initial mode uses superusers for broad endpoint coverage. Replace with role-scoped users later.
docker compose -f load_testing/docker-compose.sqlite.yml exec backend \
  python /code/load_testing/scripts/create_load_tokens.py --users 50 --superusers --fresh-tokens \
  --out /code/load_testing/users.csv

# 3. Seed 50 compliance assessments and their requirement assessments
docker compose -f load_testing/docker-compose.sqlite.yml exec backend \
  python /code/load_testing/scripts/seed_compliance_workload.py --assessments 50 --fresh \
  --out /code/load_testing/workload.json

# 4. Start Locust UI
cp -n load_testing/users.example.csv load_testing/users.csv 2>/dev/null || true
ENABLE_WRITES=true docker compose -f load_testing/docker-compose.sqlite.yml up -d locust
```

Open Locust: <http://localhost:8089>

Use:

- Host: already set to `http://caddy:8080` inside the container.
- Users: `50`
- Spawn rate: `5` users/s for a normal ramp, or higher for spike tests.

To run headless:

```bash
ENABLE_WRITES=true docker compose -f load_testing/docker-compose.sqlite.yml run --rm locust \
  -f /mnt/locust/locustfile.py \
  --host http://caddy:8080 \
  --headless -u 50 -r 5 -t 20m \
  --csv /mnt/locust/results/sqlite_50u_20m
```

For the 100-user / 100-compliance-assessment headroom scenario, create 100 users and seed 100 assessments before running Locust:

```bash
docker compose -f load_testing/docker-compose.sqlite.yml exec backend \
  python /code/load_testing/scripts/create_load_tokens.py --users 100 --superusers --fresh-tokens \
  --out /code/load_testing/users.csv

docker compose -f load_testing/docker-compose.sqlite.yml exec backend \
  python /code/load_testing/scripts/seed_compliance_workload.py --assessments 100 --fresh \
  --out /code/load_testing/workload.json

ENABLE_WRITES=true docker compose -f load_testing/docker-compose.sqlite.yml run --rm locust \
  -f /mnt/locust/locustfile.py \
  --host http://caddy:8080 \
  --headless -u 100 -r 10 -t 10m \
  --csv /mnt/locust/results/sqlite_100u_100ca_10m
```

## Quick start: PostgreSQL

Stop the SQLite lab first because both compose files expose the same ports:

```bash
docker compose -f load_testing/docker-compose.sqlite.yml down
```

Then:

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
  --headless -u 50 -r 5 -t 20m \
  --csv /mnt/locust/results/postgres_50u_20m
```

For the 100-user / 100-compliance-assessment headroom scenario:

```bash
docker compose -f load_testing/docker-compose.postgres.yml exec backend \
  python /code/load_testing/scripts/create_load_tokens.py --users 100 --superusers --fresh-tokens \
  --out /code/load_testing/users.csv

docker compose -f load_testing/docker-compose.postgres.yml exec backend \
  python /code/load_testing/scripts/seed_compliance_workload.py --assessments 100 --fresh \
  --out /code/load_testing/workload.json

ENABLE_WRITES=true docker compose -f load_testing/docker-compose.postgres.yml run --rm locust \
  -f /mnt/locust/locustfile.py \
  --host http://caddy:8080 \
  --headless -u 100 -r 10 -t 10m \
  --csv /mnt/locust/results/postgres_100u_100ca_10m
```

## Workload model

Current `locustfile.py` simulates authenticated users doing common API activity:

- list pages: folders, assessments, requirements, controls, evidence, risks, assets, findings, tasks
- detail pages for discovered objects
- dashboard-like endpoints: counters, metrics, aggregate data, preferences
- table search/filter-like requests

Writes are disabled by default, but the first realistic mixed workload is now available:

```bash
ENABLE_WRITES=true docker compose -f load_testing/docker-compose.postgres.yml up locust
```

When enabled, each simulated user repeatedly updates seeded `RequirementAssessment` rows across the seeded compliance assessments:

- flips `result`
- flips `status`
- writes a fresh `observation`
- clears `extended_result` to avoid result-dependent validation constraints

This is a good first approximation of reviewers/respondents updating audit items “left and right”. Later refinements can split users into auditor/respondent roles and use assignment-specific permissions instead of superusers.

## Important benchmark discipline

Keep these identical between SQLite and PostgreSQL runs:

- same branch/commit
- same dataset size
- same number of users/tokens
- same `GUNICORN_WORKERS`
- same Huey setting
- same Locust file and run duration
- same host machine

Suggested run matrix:

| Run | DB | Users | Duration | Purpose |
| --- | --- | ---: | ---: | --- |
| smoke | SQLite + Postgres | 5 | 5m | Validate tokens/scenario |
| target | SQLite + Postgres | 50 | 20–30m | Main comparison |
| spike | SQLite + Postgres | 50 | 10m | High spawn rate |
| headroom | SQLite + PostgreSQL | 100 | 10m | Initial 100-user comparison |
| extended headroom | PostgreSQL | 100–150 | 20–30m | Capacity margin |

## Latest benchmark snapshot

Detailed results are in `load_testing/BENCHMARK_RESULTS.md`.

| Run | Requests | Failures | Median | Avg | p95 | p99 | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SQLite 50u / 50 CA / 5m | `6286` | `0` | `39 ms` | `65 ms` | `260 ms` | `500 ms` | Passed short target run |
| PostgreSQL 50u / 50 CA / 5m | `6329` | `0` | `22 ms` | `40 ms` | `120 ms` | `390 ms` | Better normal latency |
| SQLite 100u / 100 CA / 10m | `23782` | `2` | `66 ms` | `113 ms` | `420 ms` | `1300 ms` | 2 write-path `502`s; Gunicorn worker `SIGBUS`; no `database is locked` observed |
| PostgreSQL 100u / 100 CA / 10m, 3 workers | `24174` | `0` | `39 ms` | `61 ms` | `170 ms` | `630 ms` | Passed 100-user headroom run |
| PostgreSQL 100u / 100 CA / 10m, 5 workers | `24234` | `0` | `43 ms` | `71 ms` | `200 ms` | `700 ms` | No failures, but tail latency did not improve vs 3 workers |

The 100-user comparison reinforces PostgreSQL as the safer production default for concurrent writes. SQLite completed the run but showed worker instability and worse tail latency. In the first Gunicorn comparison, 5 workers did not beat 3 workers for this 100-user workload; test 7 workers only if you need more data, otherwise keep 3 as the current baseline.

## Infra knobs to test

### Gunicorn

The backend image reads:

- `GUNICORN_WORKERS` default `3`
- `GUNICORN_TIMEOUT` default `100`
- `GUNICORN_KEEPALIVE` default `30`

For sync Gunicorn workers, start with:

```text
GUNICORN_WORKERS = min((2 * CPU cores) + 1, value allowed by memory and DB connections)
```

For a 50-user target, compare at least:

- `GUNICORN_WORKERS=3`
- `GUNICORN_WORKERS=5`
- `GUNICORN_WORKERS=7` if CPU/memory allows

Do not blindly increase workers: every worker can hold database connections and consume memory.

### PostgreSQL

The Postgres compose starts with conservative tunables:

- `POSTGRES_MAX_CONNECTIONS=200`
- `POSTGRES_SHARED_BUFFERS=512MB`
- `POSTGRES_EFFECTIVE_CACHE_SIZE=1536MB`
- `POSTGRES_WORK_MEM=8MB`

For production, size these based on actual RAM. Ensure `max_connections` covers at least:

```text
backend gunicorn workers + huey workers + admin/maintenance connections + margin
```

For larger deployments, consider PgBouncer instead of simply raising `max_connections`.

### SQLite

SQLite is included to quantify the limit, not because it is expected to be ideal for concurrent writes. Watch specifically for:

- `database is locked`
- long p99 latency during writes/background tasks
- degraded response times as Gunicorn workers increase

A later variant can test SQLite WAL mode, but PostgreSQL should be the default recommendation if 50 concurrent users include meaningful writes.

## Adding SvelteKit SSR coverage later

The API workload is the baseline. To include SSR/browser-like overhead later, add a second low-weight Locust user that uses cookie/session auth or a Playwright-based smoke load for key pages. Keep that separate from the DB comparison so frontend rendering does not obscure DB behavior.
