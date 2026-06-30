#!/usr/bin/env bash
set -euo pipefail

DOCKER_COMPOSE_FILE="docker-compose-build.yml"
EXPECTED_OWNER="1001:1001"
UNKNOWN_ARGUMENTS=()

while (($#)); do
  case "$1" in
    -f)
      shift
      if (($# == 0)); then
        printf 'Argument -f requires a compose file path.\n' >&2
        exit 1
      fi
      DOCKER_COMPOSE_FILE="$1"
      ;;
    *)
      UNKNOWN_ARGUMENTS+=("$1")
      ;;
  esac
  shift
done

if ((${#UNKNOWN_ARGUMENTS[@]} > 0)); then
  printf 'Unknown argument(s): %s. Supported arguments: -f <compose-file>.\n' "${UNKNOWN_ARGUMENTS[*]}" >&2
  exit 1
fi

prepare_meta_file() {
  VERSION=$(git describe --tags --always)
  BUILD=$(git rev-parse --short HEAD)
  echo "CISO_ASSISTANT_VERSION=${VERSION}" >.meta
  echo "CISO_ASSISTANT_BUILD=${BUILD}" >>.meta
  cp .meta ./backend/ciso_assistant/.meta
  cp .meta ./backend/.meta
}

# On macOS, GNU stat (-c) is not available by default. We use this as a simple
# Linux detector and skip chown on macOS (Docker Desktop emulates ownership).
is_linux_gnu_stat() {
  stat -c '%u:%g' . >/dev/null 2>&1
}

get_owner_linux() {
  stat -c '%u:%g' "$1"
}

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

echo "Using Docker Compose file: \"${DOCKER_COMPOSE_FILE}\""

# Check if database already exists
if [ -f db/ciso-assistant.sqlite3 ]; then
  echo "The database seems already created."
  echo "For successive runs, you can now use 'docker compose -f ${DOCKER_COMPOSE_FILE} up'."
else
  prepare_meta_file

  echo "Building containers..."
  docker compose -f "${DOCKER_COMPOSE_FILE}" build --pull

  mkdir -p ./db

  if is_linux_gnu_stat; then
    DB_OWNER="$(get_owner_linux ./db)"
    if [ "$DB_OWNER" != "$EXPECTED_OWNER" ]; then
      echo "Fixing ownership of ./db (was $DB_OWNER, expected $EXPECTED_OWNER)"
      if ! chown -R "$EXPECTED_OWNER" ./db 2>/dev/null; then
        echo "chown failed, retrying with sudo..."
        sudo chown -R "$EXPECTED_OWNER" ./db
      fi
    fi
  else
    echo "Non-Linux (no GNU stat detected): skipping ownership fix for ./db"
  fi

  echo "Starting services..."
  docker compose -f "${DOCKER_COMPOSE_FILE}" up -d

  echo "Giving some time for the database to be ready, please wait ..."
  for i in $(seq 1 60); do
    if docker compose -f "${DOCKER_COMPOSE_FILE}" exec -T backend python manage.py migrate --check >/dev/null 2>&1; then
      echo "Migrations complete."
      break
    fi
    if [ "$i" -eq 60 ]; then
      echo "Migrations did not complete within 600s. Recent backend logs:"
      docker compose -f "${DOCKER_COMPOSE_FILE}" logs --tail=50 backend
      exit 1
    fi
    sleep 10
  done

  echo "Initialize your superuser account..."
  docker compose -f "${DOCKER_COMPOSE_FILE}" exec -T backend python manage.py createsuperuser

  echo "🚀 CISO Assistant is ready!"
  echo "Connect to CISO Assistant on https://localhost:8443"
  echo "For successive runs, you can now use 'docker compose -f ${DOCKER_COMPOSE_FILE} up'."
fi
