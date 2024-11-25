#!/bin/bash

# Script to update Docker images for CISO Assistant (always using 'latest')

# Variables
DB_FILE="db/ciso-assistant.sqlite3"
BACKUP_FILE="ciso-assistant-backup.sqlite3"
BACKEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/backend:latest"
FRONTEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/frontend:latest"

echo "Using backend image: $BACKEND_IMAGE"
echo "Using frontend image: $FRONTEND_IMAGE"

# Backup the database
if [ -f "$DB_FILE" ]; then
    echo "Backing up the database file..."
    cp "$DB_FILE" "$BACKUP_FILE"
    if [ $? -eq 0 ]; then
        echo "Database backed up to $BACKUP_FILE."
    else
        echo "Error: Failed to back up the database file."
        exit 1
    fi
else
    echo "Error: Database file $DB_FILE does not exist. Skipping backup."
    exit 1
fi

# Stop running containers
echo "Stopping Docker containers..."
docker compose stop

# Remove existing container instances
echo "Removing container instances..."
docker compose rm -f

# Remove old images (any version)
echo "Removing all old backend and frontend images..."
docker images | grep "ghcr.io/intuitem/ciso-assistant-community/backend" | awk '{print $3}' | xargs -r docker rmi -f
docker images | grep "ghcr.io/intuitem/ciso-assistant-community/frontend" | awk '{print $3}' | xargs -r docker rmi -f

# Start containers with updated images
echo "Starting Docker containers with updated images..."
docker compose up -d

# Restore the database
if [ -f "$BACKUP_FILE" ]; then
    echo "Restoring the database file..."
    cp "$BACKUP_FILE" "$DB_FILE"
    if [ $? -eq 0 ]; then
        echo "Database restored to $DB_FILE."
    else
        echo "Error: Failed to restore the database file."
        exit 1
    fi
else
    echo "Error: Backup file $BACKUP_FILE does not exist. Unable to restore the database."
    exit 1
fi

echo "Update and restoration process completed successfully."
