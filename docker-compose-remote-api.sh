#! /usr/bin/env bash

if [ -f db/ciso-assistant.sqlite3 ] ; then
    echo "the database seems already created"
    echo "you should launch docker compose -f docker-compose-remote-api.yml up -d"
    echo "for clean start, you can remove the database file, run docker compose down and then docker compose rm and start again"
else
    echo "Cleaning up old images and pulling the new ones ..."
    docker rmi ghcr.io/intuitem/ciso-assistant-community/backend:latest ghcr.io/intuitem/ciso-assistant-community/frontend:latest 2> /dev/null
    docker compose -f docker-compose-remote-api.yml up -d
    docker compose -f docker-compose-remote-api.yml exec backend python manage.py migrate
    echo "initialize your superuser account..."
    docker compose -f docker-compose-remote-api.yml exec backend python manage.py createsuperuser
    echo "connect to ciso assistant on https://<your-host>:8443"
    echo "for successive runs you can now use docker compose up"
fi
