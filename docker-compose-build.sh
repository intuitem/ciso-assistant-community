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

get_uid() {
  stat -c '%u' "$1" 2>/dev/null || stat -f '%u' "$1"
}

get_gid() {
  stat -c '%g' "$1" 2>/dev/null || stat -f '%g' "$1"
}

get_owner_uid_gid() {
  echo "$(get_uid "$1"):$(get_gid "$1")"
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

  # Build and start the containers
  echo "Building containers..."
  docker compose -f "${DOCKER_COMPOSE_FILE}" build --pull

  mkdir -p ./db
  DB_OWNER="$(get_owner_uid_gid ./db)"

  if [ "$DB_OWNER" != "$EXPECTED_OWNER" ]; then
    echo "Fixing ownership of ./db (was $DB_OWNER, expected $EXPECTED_OWNER)"
    sudo chown -R "$EXPECTED_OWNER" ./db
  fi

  echo "Starting services..."
  docker compose -f "${DOCKER_COMPOSE_FILE}" up

  # Simple wait for database migrations
  echo "Giving some time for the database to be ready, please wait ..."
  sleep 50

  echo "Initialize your superuser account..."
  docker compose exec backend poetry run python manage.py createsuperuser

  echo "🚀 CISO Assistant is ready!"
  echo "Connect to CISO Assistant on https://localhost:8443"
  echo "For successive runs, you can now use 'docker compose up'."
fi
