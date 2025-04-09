#!/usr/bin/env bash
set -euo pipefail

DOCKER_COMPOSE_FILE=./samples/fullstack-build-zk-single-kafka-single.yml
DB_FILE=./samples/db/ciso-assistant.sqlite3

prepare_meta_file() {
  VERSION=$(git describe --tags --always)
  BUILD=$(git rev-parse --short HEAD)
  echo "CISO_ASSISTANT_VERSION=${VERSION}" >.meta
  echo "CISO_ASSISTANT_BUILD=${BUILD}" >>.meta
  cp .meta ../backend/ciso_assistant/.meta
  cp .meta ../backend/.meta
}

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Check if database already exists
if [ -f "${DB_FILE}" ]; then
  echo "The database seems already created."
  echo "For successive runs, you can now use 'docker compose up'."
else
  prepare_meta_file

  # Build and start the containers
  echo "Building containers..."
  docker compose -f "${DOCKER_COMPOSE_FILE}" build --pull

  echo "Starting services..."
  docker compose -f "${DOCKER_COMPOSE_FILE}" up -d

  # Simple wait for database migrations
  echo "Giving some time for the database to be ready, please wait ..."
  sleep 50

  echo "Initialize your superuser account..."
  # Prompt for superuser credentials:
  read -p "Enter superuser email: " SUPERUSER_EMAIL

  # Prompt for password and confirmation
  read -sp "Enter superuser password: " SUPERUSER_PASSWORD
  echo
  read -sp "Confirm superuser password: " SUPERUSER_PASSWORD_CONFIRM
  echo

  if [ "$SUPERUSER_PASSWORD" != "$SUPERUSER_PASSWORD_CONFIRM" ]; then
    echo "Passwords do not match. Aborting."
    exit 1
  fi

  # Pass the credentials into the container.
  docker compose -f "${DOCKER_COMPOSE_FILE}" exec -e DJANGO_SUPERUSER_EMAIL="${SUPERUSER_EMAIL}" -e DJANGO_SUPERUSER_PASSWORD="${SUPERUSER_PASSWORD}" backend \
    poetry run python manage.py createsuperuser --no-input

  echo "🚀 CISO Assistant is ready!"
  echo "Connect to CISO Assistant on https://localhost:8443"
  echo "For successive runs, you can now use 'docker compose up'."
fi
