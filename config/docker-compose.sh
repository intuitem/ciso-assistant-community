#! /bin/bash

echo "Starting CISO Assistant services..."
docker compose -f ./docker-compose.yml pull
docker compose -f ./docker-compose.yml up -d

echo "Waiting for CISO Assistant backend to be ready..."
until docker compose -f ./docker-compose.yml exec -T backend curl -f http://localhost:8000/api/build >/dev/null 2>&1; do
  echo "Backend is not ready - waiting 10s..."
  sleep 10
done

echo -e "\nBackend is ready!"
echo "Creating superuser..."
docker compose -f ./docker-compose.yml exec backend poetry run python manage.py createsuperuser

echo -e "\nInitialization complete!"
echo "You can now access CISO Assistant at https://localhost:8443 (or the port you've specified)"
