#! /usr/bin/env bash

if [ -d db/data ] ; then
    echo "the database seems already created"
    echo "you should launch docker-compose up -d"
else
    uuidgen > ./db/pg_password.txt
    docker-compose up -d
    echo "initialize your superuser account..."
    docker-compose exec ciso-assistant python manage.py createsuperuser
    echo "for successive runs you can now use docker compose up"
fi
