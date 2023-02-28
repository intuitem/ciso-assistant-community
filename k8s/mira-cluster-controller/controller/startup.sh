#!/usr/bin/env bash
# wait for database to be ready

if [ ! -n "$DJANGO_SECRET_KEY" ]; then
    if [ ! -f /code/db/django_secret_key ]; then
        cat /proc/sys/kernel/random/uuid > db/django_secret_key
        echo "generating initial Django secret key"
    fi
    export DJANGO_SECRET_KEY=$(<db/django_secret_key)
    echo "Django secret key read from file"
fi

while ! python manage.py showmigrations admin > /dev/null 2>&1; do 
    echo "database not ready; waiting"
    sleep 10
done

python manage.py makemigrations 
python manage.py migrate
if [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    python manage.py createsuperuser --noinput
fi

exec gunicorn --chdir controller  --bind :8000 --env RUN_MAIN=true controller.wsgi:application
