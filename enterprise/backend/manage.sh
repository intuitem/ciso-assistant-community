#!/usr/bin/env bash

DJANGO_DIR=../../backend
ENTERPRISE_SETTINGS=enterprise_core.settings

python $DJANGO_DIR/manage.py $@ --settings=$ENTERPRISE_SETTINGS
