#!/usr/bin/env bash
set -euo pipefail

DOCKER_COMPOSE_FILE="${1:-docker-compose-build.yml}"

prepare_meta_file() {
  VERSION=$(git describe --tags --always)
  BUILD=$(git rev-parse --short HEAD)
  echo "CISO_ASSISTANT_VERSION=${VERSION}" >.meta
  echo "CISO_ASSISTANT_BUILD=${BUILD}" >>.meta
  cp .meta ./backend/ciso_assistant/.meta
  cp .meta ./backend/.meta
}

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

prepare_meta_file

# Build and start the containers
echo "Building containers..."
docker compose -f "${DOCKER_COMPOSE_FILE}" build --pull

echo "Starting services..."
docker compose -f "${DOCKER_COMPOSE_FILE}" up -d

echo "Waiting for CISO Assistant backend to be ready..."
until docker compose -f "${DOCKER_COMPOSE_FILE}" exec -T backend curl -f http://localhost:8000/api/build >/dev/null 2>&1; do
  echo "Backend is not ready - waiting 10s..."
  sleep 10
done

echo "Initialize your superuser account..."
docker compose -f "${DOCKER_COMPOSE_FILE}" exec backend poetry run python manage.py createsuperuser

echo "🚀 CISO Assistant is ready!"
echo "Connect to CISO Assistant on https://localhost:8443"
echo "For successive runs, you can now use 'docker compose -f ${DOCKER_COMPOSE_FILE} up -d'."
