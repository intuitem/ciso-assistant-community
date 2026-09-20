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
  -h | --help)
    echo "Usage: run.sh [--reseed] [--keep-up] [-- <playwright args>]"
    echo "  --reseed   rebuild the demo database from scratch before capturing"
    echo "  --keep-up  leave the servers running after the capture"
    exit 0
    ;;
  esac
done

BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  [[ $KEEP_UP -eq 1 ]] && return
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

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
for _ in $(seq 1 60); do
  if curl -sfo /dev/null "http://localhost:$FRONTEND_PORT/login"; then break; fi
  sleep 2
done

pnpm exec playwright test --config=playwright.docs.config.ts ${PW_ARGS[@]+"${PW_ARGS[@]}"}
echo "screenshots written to product-docs/.gitbook/assets/"
