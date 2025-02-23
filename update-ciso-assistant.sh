#! /usr/bin/env bash

DB_FILE="db/ciso-assistant.sqlite3"
BACKUP_FILE="ciso-assistant-backup.sqlite3"

BACKEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/backend:latest"
FRONTEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/frontend:latest"

# Backup the database
if [ ! -f "$DB_FILE" ]; then
  echo "Error: No database found, please initialize CISO Assistant first"
  exit 1
else
  cp "$DB_FILE" "$BACKUP_FILE"
  echo "Backup of the database created in $BACKUP_FILE"
fi

# Stop the containers
docker compose rm -fs

# note: the rmi trick is not needed anymore since we move to always pull policy
# Start the containers
docker compose -f docker-compose-default.yml up -d
echo "CISO assistant updated successfully"
