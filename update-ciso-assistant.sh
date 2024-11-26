#!/bin/bash

# ---------------------------------------------------------------------------
# Manual: Database Backup and Update Script for CISO Assistant
# ---------------------------------------------------------------------------
# This script is used to backup, restore, and update the CISO Assistant database
# and Docker containers. It supports database backup and restoration, 
# version migration, and Docker image management. Below is a detailed guide 
# on how the script works and how to use it.
#
# Usage:
#   ./update-ciso-assistant.sh [OPTIONS]
#
# Options:
#   --help, -h       Display this help message
#   [version]        Specify the version of CISO Assistant to update to (default: 'latest')
#
# Example:
#   ./update-ciso-assistant.sh 1.0.0
#   This will update CISO Assistant to version 1.0.0, backing up and restoring 
#   the database as needed.
#
# Prerequisites:
# - Docker should be installed and running
# - Docker Compose should be available
# - Poetry (if used for the backend) should be available in the Docker container
#
# ---------------------------------------------------------------------------

# Display help message if --help or -h is passed as an argument
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    cat <<EOF
This script automates the process of backing up, updating, and restoring the 
CISO Assistant database and Docker containers. The following steps will be executed:

1. Back up the current database (if available).
2. Optionally, restore a backup for a specific version.
3. Remove current Docker containers and images related to CISO Assistant.
4. Pull and run the new Docker images for the specified version.
5. Run Django migrations and set up the superuser account (if the database is new).

Usage:
  ./update-ciso-assistant.sh [version]

Options:
  [version]      Specify the version of CISO Assistant to update to (default is 'latest').
  -h, --help     Show this help message.

Example:
  ./update-ciso-assistant.sh latest
EOF
    exit 0
fi

# Variables
DB_FILE="db/ciso-assistant.sqlite3"
BACKUP_DIR="../ciso-assistant-backups"
VERSION=${1:-latest}
CURRENT_VERSION=$(docker ps -a --format "{{.Image}}" | grep "ghcr.io/intuitem/ciso-assistant-community/backend" | head -n 1 | cut -d ':' -f2 || echo "latest")
BACKUP_FILE="$BACKUP_DIR/ciso-assistant-backup-$CURRENT_VERSION.sqlite3"
RESTORE_BACKUP_FILE="$BACKUP_DIR/ciso-assistant-backup-$VERSION.sqlite3"
BACKEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/backend:$VERSION"
FRONTEND_IMAGE="ghcr.io/intuitem/ciso-assistant-community/frontend:$VERSION"

echo "Using backend image: $BACKEND_IMAGE"
echo "Using frontend image: $FRONTEND_IMAGE"

# Create backup directory if it doesn't exist
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Creating backup directory at $BACKUP_DIR..."
    mkdir -p "$BACKUP_DIR" || { echo "Error: Failed to create backup directory."; exit 1; }
    echo "Backup directory created."
fi

# Backup the current database (overwrite if exists)
if [ -f "$DB_FILE" ]; then
    echo "Backing up the database for current version '$CURRENT_VERSION' (overwriting existing backup)..."
    cp "$DB_FILE" "$BACKUP_FILE" || { echo "Error: Database backup failed."; exit 1; }
    echo "Database backed up to $BACKUP_FILE."
else
    echo "Database file not found. Skipping backup."
fi

# Stop and remove containers (after backup)
docker compose down

# Remove all images
docker images | grep -E "ghcr.io/intuitem/ciso-assistant-community/(backend|frontend)" | awk '{print $3}' | xargs -r docker rmi -f

# Choice to restore the database from the selected version's backup if it exists
if [ -f "$RESTORE_BACKUP_FILE" ]; then
    read -p "Backup found for version '$VERSION'. Do you want to restore the database from this backup? (y/n): " restore_choice
    if [[ "$restore_choice" =~ ^[Yy]$ ]]; then
        echo "Restoring database from backup for version '$VERSION'..."
        cp "$RESTORE_BACKUP_FILE" "$DB_FILE" || { echo "Error: Database restoration failed."; exit 1; }
        echo "Database restored from $RESTORE_BACKUP_FILE."
    else
        echo "Skipping database restoration."
        if [ "$(echo -e "$VERSION\n$CURRENT_VERSION" | sort -V | head -n 1)" == "$CURRENT_VERSION" ] && ["$VERSION" != "$CURRENT_VERSION"]; then
            NEW_DB=true
        fi
    fi
else
    echo "No backup found for version '$VERSION'. Proceeding with a new database."
    NEW_DB=true
fi

# If using a version other than 'latest', remove the database to avoid migration conflicts (only if NEW_DB is not true)
if [ "$NEW_DB" = true ]; then
    echo "Removing database file to create a fresh one for version '$VERSION'..."
    rm -f "$DB_FILE" || { echo "Error: Failed to remove database file."; exit 1; }
    echo "Database file removed."
fi

# Pull and run the specified version
docker pull "$BACKEND_IMAGE" "$FRONTEND_IMAGE"
VERSION=$VERSION docker compose up -d

# Run Django migrations
BACKEND_CONTAINER=$(docker ps --filter "ancestor=$BACKEND_IMAGE" --format "{{.ID}}")
if [ -n "$BACKEND_CONTAINER" ]; then
    echo "Running Django migrations..."
    docker exec "$BACKEND_CONTAINER" poetry run python manage.py migrate || docker exec "$BACKEND_CONTAINER" python manage.py migrate || { echo "Error: Migration failed."; exit 1; }
    echo "Migrations completed successfully."

    # Create superuser interactively if the database is new and the version is older
    if [ "$NEW_DB" = true ]; then
        echo "Initializing your superuser account..."
        docker compose exec backend poetry run python manage.py createsuperuser || docker exec -it "$BACKEND_CONTAINER" python manage.py createsuperuser || { echo "Error: Failed to create superuser."; exit 1; }
        echo "Superuser created successfully."
    fi
else
    echo "Error: Backend container not found. Cannot run migrations or create superuser."
    exit 1
fi

echo "Update and migration for version '$VERSION' completed successfully."
