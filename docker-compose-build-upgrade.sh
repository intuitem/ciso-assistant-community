#!/usr/bin/env bash

prepare_meta_file() {
    VERSION=$(git describe --tags --always)
    BUILD=$(git rev-parse --short HEAD)

    echo "CISO_ASSISTANT_VERSION=${VERSION}" > .meta
    echo "CISO_ASSISTANT_BUILD=${BUILD}" >> .meta

    cp .meta ./backend/ciso_assistant/.meta
    cp .meta ./backend/.meta
}

prepare_meta_file

# Remove old container and images
docker compose rm -fs
docker rmi -f $(docker images -aq -f reference=ciso-assistant*)

# Build and start the containers
docker compose -f docker-compose-build.yml build
docker compose -f docker-compose-build.yml up -d

# Perform database migrations
docker compose exec backend python manage.py migrate

echo "Connect to CISO Assistant on https://localhost:8443"
echo "For successive runs, you can now use 'docker compose up'."