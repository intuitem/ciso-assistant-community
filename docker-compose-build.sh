#!/usr/bin/env bash
set -euo pipefail

DOCKER_COMPOSE_FILE=docker-compose-build.yml
EXPECTED_OWNER="1001:1001"

prepare_meta_file() {
  VERSION=$(git describe --tags --always)
  BUILD=$(git rev-parse --short HEAD)
  echo "CISO_ASSISTANT_VERSION=${VERSION}" > .meta
  echo "CISO_ASSISTANT_BUILD=${BUILD}" >> .meta
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

# Check if database already exists
if [ -f db/ciso-assistant.sqlite3 ]; then
  echo "The database seems already created."
  echo "For successive runs, you can now use 'docker compose up'."
else
  prepare_meta_file

  echo "Building containers..."
  docker compose -f "${DOCKER_COMPOSE_FILE}" build --pull

  mkdir -p ./db

  if is_linux_gnu_stat; then
    DB_OWNER="$(get_owner_linux ./db)"
    if [ "$DB_OWNER" != "$EXPECTED_OWNER" ]; then
      echo "Fixing ownership of ./db (was $DB_OWNER, expected $EXPECTED_OWNER)"
      sudo chown -R "$EXPECTED_OWNER" ./db
    fi
  else
    echo "Non-Linux (no GNU stat detected): skipping ownership fix for ./db"
  fi

  echo "Starting services..."
  docker compose -f "${DOCKER_COMPOSE_FILE}" up

  echo "Giving some time for the database to be ready, please wait ..."
  sleep 50

  echo "Initialize your superuser account..."
  docker compose exec backend poetry run python manage.py createsuperuser

  echo "🚀 CISO Assistant is ready!"
  echo "Connect to CISO Assistant on https://localhost:8443"
  echo "For successive runs, you can now use 'docker compose up'."
fi
