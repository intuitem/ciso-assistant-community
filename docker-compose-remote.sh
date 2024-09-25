#! /usr/bin/env bash

if [ -f db/ciso-assistant.sqlite3 ] ; then
    echo "the database seems already created"
    echo "you should launch docker compose -f docker-compose-remote.yml up -d"
    echo "for clean start, you can remove the database file, run docker compose down and then docker compose rm and start again"
else
    docker rmi ghcr.io/intuitem/ciso-assistant-community/backend:latest ghcr.io/intuitem/ciso-assistant-community/frontend:latest 2> /dev/null
    docker compose -f docker-compose-remote.yml up -d
    echo "Giving some time for the database to be ready, please wait ..."
    sleep 20
    echo "initialize your superuser account..."
    docker compose exec backend python manage.py createsuperuser
    echo "connect to ciso assistant on https://cool-vm:8443"
    echo "for successive runs you can now use docker compose up"
fi
