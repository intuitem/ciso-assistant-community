#!/usr/bin/env bash

usage() {
	echo "Usage: $0 [-f <path to docker-compose file>]" 1>&2
	exit 1
}

DOCKER_COMPOSE_FILE=docker-compose-build.yml

while getopts ":f:" o; do
	case "${o}" in
	f)
		if [[ -f "${OPTARG}" ]]; then
			DOCKER_COMPOSE_FILE=${OPTARG}
		else
			echo "File not found"
		fi
		;;
	*)
		usage
		;;
	esac
done
shift $((OPTIND - 1))

prepare_meta_file() {
	VERSION=$(git describe --tags --always)
	BUILD=$(git rev-parse --short HEAD)

	echo "CISO_ASSISTANT_VERSION=${VERSION}" >.meta
	echo "CISO_ASSISTANT_BUILD=${BUILD}" >>.meta

	cp .meta ./backend/ciso_assistant/.meta
	cp .meta ./backend/.meta
}

# Check if the database already exists
if [ -f db/ciso-assistant.sqlite3 ]; then
	echo "The database seems already created."
	echo "You should launch 'docker compose up -d'."
else
	prepare_meta_file

	# Build and start the containers
	docker compose -f "${DOCKER_COMPOSE_FILE}" build
	docker compose -f "${DOCKER_COMPOSE_FILE}" up -d

	# Perform database migrations
	docker compose exec backend python manage.py migrate

	# Initialize the superuser account
	echo "Initialize your superuser account..."
	docker compose exec backend python manage.py createsuperuser

	echo "Connect to CISO Assistant on https://localhost:8443"
	echo "For successive runs, you can now use 'docker compose up'."
fi
