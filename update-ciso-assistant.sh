#!/bin/bash

# Variables
DB_FILE="db/ciso-assistant.sqlite3"
BACKUP_FILE="../ciso-assistant-backup.sqlite3"
BACKEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/backend:latest"
FRONTEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/frontend:latest"

# Backup database
[ -f "$DB_FILE" ] && cp "$DB_FILE" "$BACKUP_FILE" || { echo "Database not found. Skipping."; exit 1; }

# Update Docker images
docker compose down
docker images | grep -E "ghcr.io/intuitem/ciso-assistant-community/(backend|frontend).*latest" | awk '{print $3}' | xargs -r docker rmi -f
docker pull "$BACKEND_IMAGE" "$FRONTEND_IMAGE"

# Start containers
docker compose up -d

# Run Django migrations
BACKEND_CONTAINER=$(docker ps --filter "ancestor=$BACKEND_IMAGE" --format "{{.ID}}")
[ -n "$BACKEND_CONTAINER" ] && docker exec "$BACKEND_CONTAINER" poetry run python manage.py migrate || { echo "Migration failed."; exit 1; }

echo "Update and migration completed successfully."
