#!/usr/bin/env bash

export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib
DJANGO_DIR=../../backend
ENTERPRISE_SETTINGS=enterprise_core.settings

export DJANGO_BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 "$DJANGO_DIR/manage.py" "$@" --settings="$ENTERPRISE_SETTINGS"
