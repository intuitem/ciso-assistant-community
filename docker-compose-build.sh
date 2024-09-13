#!/usr/bin/env bash

prepare_meta_file() {
    VERSION=$(git describe --tags --always)
    BUILD=$(git rev-parse --short HEAD)

    echo "CISO_ASSISTANT_VERSION=${VERSION}" > .meta
    echo "CISO_ASSISTANT_BUILD=${BUILD}" >> .meta

    cp .meta ./backend/ciso_assistant/.meta
    cp .meta ./backend/.meta
}

# Check if the database already exists
if [ -f db/ciso-assistant.sqlite3 ]; then
    echo "The database seems already created."
    echo "You should launch 'docker compose -f docker-compose-build.yml up -d'."
else
    prepare_meta_file

    # Build and start the containers
    docker compose -f docker-compose-build.yml build
    docker compose -f docker-compose-build.yml up -d

    # Perform database migrations
    docker compose exec backend python manage.py migrate

    # Initialize the superuser account
    echo "Initialize your superuser account..."
    docker compose exec backend python manage.py createsuperuser

    echo "Connect to CISO Assistant on https://localhost:8443"
    echo "For successive runs, you can now use 'docker compose up'."
fi
