#!/usr/bin/env bash
# deliver static token to initiate 2FA

if [ $# -eq 0 ]
  then
    echo "usage: createsuperuser.sh <superuser email>"
    exit 1
fi

email=$1

export DJANGO_SECRET_KEY=$(<db/django_secret_key)
python manage.py createsuperuser --username $email --email $email
echo "Use the following static tocken for first login:"
python manage.py addstatictoken $email
