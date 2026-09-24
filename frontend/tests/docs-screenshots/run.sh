#! /usr/bin/env bash
# Bring up an isolated demo stack, seed the deterministic dataset, and capture
# the documentation screenshots into product-docs/.gitbook/assets/.
#
# Deliberately does NOT reuse the e2e ports or database: e2e-tests.sh owns
# 8173/db/test-database.sqlite3, and two runs sharing a SQLite file corrupt each
# other's state.
set -euo pipefail

APP_DIR=$(cd "$(dirname "$0")/../../.." && pwd)
BACKEND_PORT=${DOCS_SHOTS_BACKEND_PORT:-8273}
FRONTEND_PORT=${DOCS_SHOTS_FRONTEND_PORT:-5273}
DB_NAME=${DOCS_SHOTS_DB:-docs-shots.sqlite3}
# The repo keeps its venv at the root, but a git worktree has none — fall back
# to uv, which resolves the project environment on its own.
if [[ -n "${DOCS_SHOTS_PYTHON:-}" ]]; then
  PYTHON=$DOCS_SHOTS_PYTHON
elif [[ -x "$APP_DIR/.venv/bin/python" ]]; then
  PYTHON=$APP_DIR/.venv/bin/python
else
  PYTHON="uv run python3"
fi

RESEED=0
KEEP_UP=0
BOOTSTRAP=0
ATTACH=0
PW_ARGS=()
PASSTHROUGH=0
for arg in "$@"; do
  if [[ $PASSTHROUGH -eq 1 ]]; then
    PW_ARGS+=("$arg")
    continue
  fi
  case $arg in
  --) PASSTHROUGH=1 ;;
  --reseed) RESEED=1 ;;
  --keep-up) KEEP_UP=1 ;;
  --bootstrap) BOOTSTRAP=1 ;;
  --attach) ATTACH=1 ;;
  -h | --help)
    echo "Usage: run.sh [--attach] [--reseed] [--keep-up] [-- <playwright args>]"
    echo
    echo "Default (fixture mode): rebuilds the demo database, starts its own"
    echo "backend and dev server, and captures reproducible screenshots."
    echo
    echo "  --attach    capture against an ALREADY RUNNING stack instead —"
    echo "              for documenting a feature you just built, with the data"
    echo "              you built it against. Not reproducible; see README."
    echo "  --reseed    rebuild the demo database from scratch before capturing"
    echo "  --keep-up   leave the servers running after the capture"
    echo "  --bootstrap install node_modules and the Playwright browser first"
    echo
    echo "Env: DOCS_SHOTS_BASE_URL, DOCS_SHOTS_EMAIL, DOCS_SHOTS_PASSWORD,"
    echo "     DOCS_SHOTS_BACKEND_PORT, DOCS_SHOTS_FRONTEND_PORT, DOCS_SHOTS_DB"
    exit 0
    ;;
  esac
done

# --- preflight -------------------------------------------------------------
# A fresh container has none of this. Fail with something actionable rather
# than letting the capture die on an opaque navigation timeout 90 seconds in.
missing=()
command -v pnpm >/dev/null || missing+=("pnpm (corepack enable && corepack prepare pnpm@latest --activate)")
$PYTHON -c '' >/dev/null 2>&1 || missing+=("a usable python ($PYTHON) — set DOCS_SHOTS_PYTHON, or install uv")
if ((${#missing[@]})); then
  printf 'docs-screenshots: missing prerequisites:\n' >&2
  printf '  - %s\n' "${missing[@]}" >&2
  exit 1
fi

if [[ $BOOTSTRAP -eq 1 ]]; then
  echo "bootstrapping frontend dependencies..."
  (cd "$APP_DIR/frontend" && pnpm install --frozen-lockfile)
  # install-deps needs root apt and network; it is the step most likely to be
  # unavailable in a sandbox, so a failure here is reported but not fatal —
  # many images already ship the shared libraries chromium needs.
  (cd "$APP_DIR/frontend" && pnpm exec playwright install-deps chromium) ||
    echo "docs-screenshots: playwright install-deps failed; continuing with the image's own libraries" >&2
  (cd "$APP_DIR/frontend" && pnpm exec playwright install chromium)
fi

if [[ ! -d "$APP_DIR/frontend/node_modules" ]]; then
  echo "docs-screenshots: frontend/node_modules is missing — run with --bootstrap" >&2
  exit 1
fi

BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  [[ $KEEP_UP -eq 1 ]] && return
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

if [[ $ATTACH -eq 1 ]]; then
  # Capture against a stack the developer is already running, with whatever
  # data they built the feature against. Nothing is seeded and no server is
  # started, so this is NOT reproducible — use it to document something you
  # just built, then move the shot into the fixture once the feature settles.
  # No default URL on purpose: attach writes straight into
  # product-docs/.gitbook/assets/, and defaulting to the usual dev port makes it
  # far too easy to overwrite the whole fixture-generated set with shots of
  # whatever happened to be listening.
  if [[ -z "${DOCS_SHOTS_BASE_URL:-}" ]]; then
    echo "docs-screenshots: --attach needs DOCS_SHOTS_BASE_URL set explicitly" >&2
    echo "  e.g. DOCS_SHOTS_BASE_URL=http://localhost:5173 run.sh --attach -- --grep my-shot" >&2
    exit 1
  fi
  # Likewise, require an explicit selection so a stray run cannot silently
  # replace every committed screenshot with non-reproducible ones.
  if ! printf '%s\n' ${PW_ARGS[@]+"${PW_ARGS[@]}"} | grep -q -- '--grep'; then
    echo "docs-screenshots: --attach needs an explicit selection, e.g. -- --grep <slug>" >&2
    exit 1
  fi
  BASE_URL=$DOCS_SHOTS_BASE_URL
  if ! curl -sfo /dev/null "$BASE_URL/login"; then
    echo "docs-screenshots: nothing answering at $BASE_URL" >&2
    exit 1
  fi
  echo "attaching to $BASE_URL (no seeding — these shots are NOT reproducible)"
  cd "$APP_DIR/frontend"
  pnpm exec playwright test --config=playwright.docs.config.ts ${PW_ARGS[@]+"${PW_ARGS[@]}"}
  echo "screenshots written to product-docs/.gitbook/assets/"
  exit 0
fi

unset POSTGRES_NAME POSTGRES_USER POSTGRES_PASSWORD
export SQLITE_FILE="db/$DB_NAME"
export DJANGO_DEBUG=True
export ALLOWED_HOSTS=localhost,127.0.0.1
export CISO_ASSISTANT_URL="http://localhost:$FRONTEND_PORT"
export DJANGO_SUPERUSER_EMAIL=${DOCS_SHOTS_EMAIL:-admin@demo.local}
export DJANGO_SUPERUSER_PASSWORD=${DOCS_SHOTS_PASSWORD:-Demo1234!}
# WeasyPrint is imported at module scope by core.views; without this every
# request that touches the URL resolver fails to load libgobject on macOS.
if [[ "$(uname)" == "Darwin" && -d /opt/homebrew/lib ]]; then
  export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib
fi

cd "$APP_DIR/backend"
if [[ $RESEED -eq 1 || ! -f "db/$DB_NAME" ]]; then
  rm -f "db/$DB_NAME"
  $PYTHON manage.py setup_cache_table
  $PYTHON manage.py migrate
  $PYTHON manage.py createsuperuser --noinput
fi
$PYTHON manage.py seed_docs_demo --flush

$PYTHON manage.py runserver "$BACKEND_PORT" --noreload >/dev/null 2>&1 &
BACKEND_PID=$!

cd "$APP_DIR/frontend"
export PUBLIC_BACKEND_API_URL="http://localhost:$BACKEND_PORT/api"
export ORIGIN="http://localhost:$FRONTEND_PORT"
export DOCS_SHOTS_BASE_URL="http://localhost:$FRONTEND_PORT"
pnpm run dev --port "$FRONTEND_PORT" --strictPort >/dev/null 2>&1 &
FRONTEND_PID=$!

echo "waiting for http://localhost:$FRONTEND_PORT ..."
READY=0
for _ in $(seq 1 60); do
  if curl -sfo /dev/null "http://localhost:$FRONTEND_PORT/login"; then
    READY=1
    break
  fi
  sleep 2
done
if [[ $READY -eq 0 ]]; then
  # Without this the capture starts against a dead server and every shot fails
  # as an opaque navigation timeout rather than a startup error.
  echo "frontend did not come up on port $FRONTEND_PORT after 120s" >&2
  exit 1
fi

pnpm exec playwright test --config=playwright.docs.config.ts ${PW_ARGS[@]+"${PW_ARGS[@]}"}
echo "screenshots written to product-docs/.gitbook/assets/"
