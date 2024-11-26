#!/bin/bash

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
