#!/usr/bin/env sh

SRC_DIR="$(
	cd -- "$(dirname "$0")" >/dev/null 2>&1
	pwd -P
)"
BASE_DIR="$(cd $SRC_DIR/../.. && pwd -P)"
BUILD_DIR="$BASE_DIR/backend"

cp $SRC_DIR/ciso_assistant/settings.py $BUILD_DIR/ciso_assistant/enterprise_settings.py
