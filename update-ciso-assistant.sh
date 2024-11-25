#!/bin/bash

# Script to update Docker images for CISO Assistant (always using 'latest')

# Variables
DB_FILE="db/ciso-assistant.sqlite3"
BACKUP_FILE="../ciso-assistant-backup.sqlite3"
BACKEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/backend:latest"
FRONTEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/frontend:latest"

echo "Using backend image: $BACKEND_IMAGE"
echo "Using frontend image: $FRONTEND_IMAGE"

# Backup the database
if [ -f "$DB_FILE" ]; then
    echo "Backing up the database file..."
    if cp "$DB_FILE" "$BACKUP_FILE"; then
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
if docker compose stop; then
    echo "Containers stopped successfully."
else
    echo "Error: Failed to stop Docker containers."
    exit 1
fi

# Remove existing container instances
echo "Removing container instances..."
if docker compose rm -f; then
    echo "Container instances removed successfully."
else
    echo "Error: Failed to remove container instances."
    exit 1
fi

# Remove old images (any version)
echo "Removing all old backend and frontend images..."
if docker images | grep "ghcr.io/intuitem/ciso-assistant-community/backend" | awk '{print $3}' | xargs -r docker rmi -f; then
    echo "Old backend images removed successfully."
else
    echo "Error: Failed to remove old backend images."
    exit 1
fi

if docker images | grep "ghcr.io/intuitem/ciso-assistant-community/frontend" | awk '{print $3}' | xargs -r docker rmi -f; then
    echo "Old frontend images removed successfully."
else
    echo "Error: Failed to remove old frontend images."
    exit 1
fi

# Pull the latest images
echo "Pulling latest images..."
if docker pull "$BACKEND_IMAGE" && docker pull "$FRONTEND_IMAGE"; then
    echo "Images pulled successfully."
else
    echo "Error: Failed to pull the latest images."
    exit 1
fi

# Start containers with updated images
echo "Starting Docker containers with updated images..."
if docker compose up -d; then
    echo "Containers started successfully."
else
    echo "Error: Failed to start Docker containers."
    exit 1
fi

# Restore the database
if [ -f "$BACKUP_FILE" ]; then
    echo "Restoring the database file..."
    if cp "$BACKUP_FILE" "$DB_FILE"; then
        echo "Database restored to $DB_FILE."
    else
        echo "Error: Failed to restore the database file."
        exit 1
    fi
else
    echo "Error: Backup file $BACKUP_FILE does not exist. Unable to restore the database."
    exit 1
fi

echo "Update and restoration process completed 
