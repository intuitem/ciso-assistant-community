#! /usr/bin/env bash

VERSION=${1:-community}

if [ "$VERSION" = "enterprise" ]; then
  # Go to the enterprise directory
  cd "enterprise/" || exit 1
fi

DB_FILE="db/ciso-assistant.sqlite3"
BACKUP_FILE="ciso-assistant-backup.sqlite3"

if [ "$VERSION" = "enterprise" ]; then
  BACKEND_IMAGE="ghcr.io/intuitem/ciso-assistant-enterprise-backend:latest"
  FRONTEND_IMAGE="ghcr.io/intuitem/ciso-assistant-enterprise-frontend:latest"
else
  BACKEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/backend:latest"
  FRONTEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/frontend:latest"
fi

echo "Update of the version : $VERSION"

# Backup the database
if [ ! -f "$DB_FILE" ]; then
  echo "Error: No database found, please initialize CISO Assistant first"
  exit 1
else
  cp "$DB_FILE" "$BACKUP_FILE"
  echo "Backup of the database created in $BACKUP_FILE"
fi

# Stop the containers
docker compose down

# Remove the images
docker rmi "$BACKEND_IMAGE" "$FRONTEND_IMAGE" 2>/dev/null

# Start the containers
docker compose up -d
echo "CISO assistant updated successfully"
