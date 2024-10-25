#!/usr/bin/env bash
# wait for database to be ready

if [ ! -n "$DJANGO_SETTINGS_MODULE" ]; then
	export DJANGO_SETTINGS_MODULE=ciso_assistant.settings
fi

if [ ! -n "$DJANGO_SECRET_KEY" ]; then
	if [ ! -f db/django_secret_key ]; then
		cat /proc/sys/kernel/random/uuid >db/django_secret_key
		echo "generating initial Django secret key"
	fi
	export DJANGO_SECRET_KEY=$(<db/django_secret_key)
	echo "Django secret key read from file"
fi

while ! python manage.py showmigrations iam >/dev/null; do
	echo "database not ready; waiting"
	sleep 10
done

poetry run python manage.py migrate --settings="${DJANGO_SETTINGS_MODULE}"
poetry run python manage.py storelibraries --settings="${DJANGO_SETTINGS_MODULE}"
if [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
	poetry run python manage.py createsuperuser --noinput --settings="${DJANGO_SETTINGS_MODULE}"
fi

exec gunicorn --chdir ciso_assistant --bind :8000 --timeout 300 --env RUN_MAIN=true ciso_assistant.wsgi:application
