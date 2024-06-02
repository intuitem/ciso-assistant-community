#! /usr/bin/env bash

echo "This is a sample for running the CISO Assistant Community Edition with a PostgreSQL database"
echo "You should adjust the docker-compose-pg.yml file with right credentials and settings and most likely split the db on a separate server in a production environment"

if [ -d ./db ] ; then
    echo "the database seems already created"
    echo "you should launch docker compose -f docker-compose-pg.yml up -d"
    echo "for clean start, you can remove the database folder and files, run docker compose down and then docker compose rm and start again"
else
    docker rmi ghcr.io/intuitem/ciso-assistant-community/backend:latest ghcr.io/intuitem/ciso-assistant-community/frontend:latest 2> /dev/null
    docker compose -f docker-compose-pg.yml up -d
    docker compose -f docker-compose-pg.yml exec backend python manage.py migrate
    echo "initialize your superuser account..."
    docker compose -f docker-compose-pg.yml exec backend python manage.py createsuperuser
    echo "connect to ciso assistant on https://localhost:8443 or the custom url if you have set it"
    echo "for successive runs you can now use docker compose -f docker-compose-pg.yml up"
fi
