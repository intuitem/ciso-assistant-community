#! /bin/bash
set -euo pipefail

if [ ! -f ./docker-compose-custom.yml ]; then
  echo "Docker compose file doesn't exist. Run 'python3 make_config.py' first."
  exit 1
fi

if [ -d ./db ]; then
  echo "The database seems already created. You should launch 'docker compose up -d' instead."
  echo "For a clean start, you can remove the db folder, and then run 'docker compose rm -fs' and start over"
  exit 1
fi

cp ./docker-compose-custom.yml ../docker-compose.yml

echo "Starting CISO Assistant services..."
docker compose -f ./docker-compose-custom.yml pull
echo "Initializing the database. This can take up to 3 minutes, please wait.."
docker compose -f ./docker-compose-custom.yml up -d

echo "Waiting for CISO Assistant backend to be ready..."
until docker compose -f ./docker-compose-custom.yml exec -T backend curl -f http://localhost:8000/api/build >/dev/null 2>&1; do
  echo "Backend is not ready - waiting 10s..."
  sleep 10
done

echo -e "Backend is ready!"
echo "Creating superuser..."
docker compose -f ./docker-compose-custom.yml exec backend poetry run python manage.py createsuperuser

echo -e "Initialization complete!"
echo "You can now access CISO Assistant at https://localhost:8443 (or the host:port you've specified)"
