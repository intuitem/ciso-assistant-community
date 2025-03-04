#! /bin/bash
set -euo pipefail

if [ -d ./db ]; then
  echo "The database seems already created. You should launch 'docker compose -f ./docker-compose-default.yml up -d' instead."
  echo "For a clean start, you can remove the db folder, and then run 'docker compose -f ./docker-compose-default.yml rm -fs' and start over"
  exit 1
fi
mkdir db
if [[ "$(uname -s)" == "Linux" ]]; then
  echo "need to change the owner of the db directory with sudo"
  sudo chown 1001:1001 db
fi
echo "Starting CISO Assistant services..."
docker compose -f ./docker-compose-default.yml pull
echo "Initializing the database. This can take up to 2 minutes, please wait.."
docker compose -f ./docker-compose-default.yml up -d

echo "Waiting for CISO Assistant backend to be ready..."
until docker compose -f ./docker-compose-default.yml exec -T backend curl -f http://localhost:8000/api/build >/dev/null 2>&1; do
  echo "Backend is not ready - waiting 10s..."
  sleep 10
done

echo -e "Backend is ready!"
echo "Creating superuser..."
docker compose -f ./docker-compose-default.yml exec backend poetry run python manage.py createsuperuser

echo -e "Initialization complete!"
echo "You can now access CISO Assistant at https://localhost:8443 (or the host:port you've specified)"

