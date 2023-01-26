#!/usr/bin/env bash

python manage.py makemigrations cal core iam
python manage.py migrate
python manage.py makemessages -i venv -l fr
python manage.py compilemessages -i venv -l fr
python manage.py createsuperuser --email root@example.com --noinput
python manage.py runserver 0.0.0.0:8000
#gunicorn --chdir asf_rm --bind :8000 asf_rm.wsgi:application
