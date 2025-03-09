#!/usr/bin/env bash

# Simple script to migrate a local dir ("db") to Docker named volumes:
#   - <prefix>db for the backend and huey
#   - <prefix>caddy_data for Caddy (ONLY IF "caddy" exists)
# Default prefix: "ciso-assistant-community_"
# Usage: docker-migrate-dir-to-volume.sh <path_to_db_dir> [optional_prefix]

# Check if at least one argument (directory path) is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_db_dir> [optional_prefix]"
    exit 1
fi

# Resolve full path to avoid issues with relative paths
DB_DIR="$(realpath "$1")"

# Check if the directory exists
if [ ! -d "$DB_DIR" ]; then
    echo "❌ Error: Directory '$DB_DIR' does not exist."
    exit 1
fi

# Set volume prefix (default: "ciso-assistant-community_")
VOLUME_PREFIX="${2:-ciso-assistant-community_}"

# Define main volume
DB_VOLUME="${VOLUME_PREFIX}db"

echo "📦 Creating Docker volume for the database..."
docker volume create "$DB_VOLUME"

echo "📂 Copying contents of '$DB_DIR' to '$DB_VOLUME' volume..."
docker run --rm -v "$DB_VOLUME":/mnt/volume -v "$DB_DIR":/mnt/source ubuntu bash -c "cp -r /mnt/source/. /mnt/volume/ && chown -R 1001:1001 /mnt/volume"

# Check if the "caddy" directory exists before creating the volume
if [ -d "$DB_DIR/caddy" ]; then
    CADDY_VOLUME="${VOLUME_PREFIX}caddy_data"
    
    echo "📦 Creating Docker volume for Caddy..."
    docker volume create "$CADDY_VOLUME"

    echo "📂 Copying 'caddy' contents to '$CADDY_VOLUME' volume..."
    docker run --rm -v "$CADDY_VOLUME":/mnt/volume -v "$DB_DIR/caddy":/mnt/source ubuntu bash -c "cp -r /mnt/source/. /mnt/volume/"
    
    echo "✅ '$CADDY_VOLUME' copied successfully."
else
    echo "⚠️ 'caddy' directory not found. Skipping volume creation."
fi

echo "✅ Migration complete! Volumes are ready to use."
