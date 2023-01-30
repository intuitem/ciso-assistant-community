#!/usr/bin/env bash

# wait for database to be ready
while ! python manage.py showmigrations iam > /dev/null 2>&1; do 
echo "database not ready; waiting"
sleep 10
done

python manage.py makemigrations cal core iam
python manage.py migrate
python manage.py makemessages -i venv -l fr
python manage.py compilemessages -i venv -l fr

# the next command will fail if already created, this is assumed
python manage.py createsuperuser --email root@example.com --noinput
python manage.py collectstatic --no-input --clear
#python manage.py runserver 0.0.0.0:8000
#gunicorn --chdir asf_rm --bind :8000 asf_rm.wsgi:application
