#! /bin/bash
set -euo pipefail

EXPECTED_OWNER="1001:1001"
DOCKER_COMPOSE_FILE="./docker-compose-custom.yml"
MIGRATION_CHECK_ATTEMPTS=60
MIGRATION_CHECK_DELAY_SECONDS=10

is_linux_gnu_stat() {
  stat -c '%u:%g' . >/dev/null 2>&1
}

get_owner_linux() {
  stat -c '%u:%g' "$1"
}

wait_for_migrations() {
  for i in $(seq 1 "$MIGRATION_CHECK_ATTEMPTS"); do
    if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T backend python manage.py migrate --check >/dev/null 2>&1; then
      echo "Migrations complete."
      return
    fi

    if [ "$i" -eq "$MIGRATION_CHECK_ATTEMPTS" ]; then
      timeout_seconds=$((MIGRATION_CHECK_ATTEMPTS * MIGRATION_CHECK_DELAY_SECONDS))
      echo "Migrations did not complete within ${timeout_seconds}s. Recent backend logs:"
      docker compose -f "$DOCKER_COMPOSE_FILE" logs --tail=50 backend
      exit 1
    fi

    sleep "$MIGRATION_CHECK_DELAY_SECONDS"
  done
}

if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
  echo "Docker compose file doesn't exist. Run 'python3 make_config.py' first."
  exit 1
fi

if [ -d ./db ]; then
  echo "The database seems already created. You should launch 'docker compose up -d' instead."
  echo "For a clean start, you can remove the db folder, and then run 'docker compose rm -fs' and start over"
  exit 1
fi

cp "$DOCKER_COMPOSE_FILE" ../docker-compose.yml

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

echo "Starting CISO Assistant services..."
docker compose -f "$DOCKER_COMPOSE_FILE" pull
echo "Giving some time for the database to be ready, please wait ..."
docker compose -f "$DOCKER_COMPOSE_FILE" up -d

wait_for_migrations

echo "Creating superuser..."
docker compose -f "$DOCKER_COMPOSE_FILE" exec backend python manage.py createsuperuser

echo -e "Initialization complete!"
echo "You can now access CISO Assistant at https://localhost:8443 (or the host:port you've specified)"
