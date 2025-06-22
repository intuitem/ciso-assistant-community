#! /usr/bin/env bash
set -euo pipefail

DB_FILE="db/ciso-assistant.sqlite3"
BACKUP_FILE="ciso-assistant-backup.sqlite3"

# Backup the database
if [ ! -f "$DB_FILE" ]; then
  echo "Error: No database found, please initialize CISO Assistant first"
  exit 1
else
  cp "$DB_FILE" "$BACKUP_FILE"
  echo "Backup of the database created in $BACKUP_FILE"
fi

# Stop and clean the containers
docker compose rm -fs

# note: the rmi trick is not needed anymore since we move to always pull policy
# Start the containers
docker compose up -d
echo "CISO assistant updated successfully"
