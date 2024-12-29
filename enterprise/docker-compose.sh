#! /usr/bin/env bash

if [ -f db/ciso-assistant.sqlite3 ]; then
  echo "the database seems already created"
  echo "you should launch docker compose up -d"
  echo "for clean start, you can remove the database file, run docker compose down and then docker compose rm and start again"
else
  docker rmi ghcr.io/intuitem/ciso-assistant-enterprise-backend:latest ghcr.io/intuitem/ciso-assistant-enterprise-frontend:latest 2>/dev/null
  docker compose up -d
  echo "Giving some time for the database to be ready, please wait ..."
  sleep 50
  echo "initialize your superuser account..."
  docker compose exec backend poetry run python manage.py createsuperuser
  echo "connect to ciso assistant on https://localhost:9443"
  echo "for successive runs you can now use docker compose up"
fi
