#! /usr/bin/env bash

if [ -f db/ciso-assistant.sqlite3 ] ; then
    echo "the database seems already created"
    echo "you should launch docker compose up -d"
else
    docker compose -f docker-compose-build.yml build 
    docker compose -f docker-compose-build.yml up -d
    docker compose exec backend python manage.py migrate
    echo "initialize your superuser account..."
    docker compose exec backend python manage.py createsuperuser
    echo "connect to ciso assistant on https://localhost:8443"
    echo "for successive runs you can now use docker compose up"
fi
