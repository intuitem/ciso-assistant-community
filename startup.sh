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
if [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    python manage.py createsuperuser --noinput
fi
exec gunicorn --chdir asf_rm --bind :8000 --env RUN_MAIN=true asf_rm.wsgi:application
