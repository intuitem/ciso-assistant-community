#!/usr/bin/env bash

DJANGO_DIR=../../backend
ENTERPRISE_SETTINGS=enterprise_core.settings

export DJANGO_BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

python $DJANGO_DIR/manage.py $@ --settings=$ENTERPRISE_SETTINGS
