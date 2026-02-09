#! /bin/bash
set -euo pipefail

DOCKER_COMPOSE_FILE=docker-compose.yml
EXPECTED_OWNER="1001:1001"

get_uid() {
  stat -c '%u' "$1" 2>/dev/null || stat -f '%u' "$1"
}

get_gid() {
  stat -c '%g' "$1" 2>/dev/null || stat -f '%g' "$1"
}

get_owner_uid_gid() {
  echo "$(get_uid "$1"):$(get_gid "$1")"
}

if [ -d ./db ]; then
  echo "The database seems already created. You should launch 'docker compose up -d' instead."
  echo "For a clean start, you can remove the db folder, and then run 'docker compose rm -fs' and start over"
  exit 1
fi

mkdir -p ./db
DB_OWNER="$(get_owner_uid_gid ./db)"

if [ "$DB_OWNER" != "$EXPECTED_OWNER" ]; then
  echo "Fixing ownership of ./db (was $DB_OWNER, expected $EXPECTED_OWNER)"
  sudo chown -R "$EXPECTED_OWNER" ./db
fi

echo "Starting CISO Assistant services..."
docker compose -f "${DOCKER_COMPOSE_FILE}" pull
echo "Initializing the database. This can take up to 2 minutes, please wait.."

docker compose -f "${DOCKER_COMPOSE_FILE}" up -d

echo "Waiting for CISO Assistant backend to be ready..."
until docker compose -f "${DOCKER_COMPOSE_FILE}" exec -T backend curl -f http://localhost:8000/api/health/ >/dev/null 2>&1; do
  echo "Backend is not ready - waiting 10s..."
  sleep 10
done

echo "Backend is ready!"
echo "Creating superuser..."
docker compose -f "${DOCKER_COMPOSE_FILE}" exec backend poetry run python manage.py createsuperuser

echo "Initialization complete!"
echo "You can now access CISO Assistant at https://localhost:8443 (or the host:port you've specified)"
