#!/usr/bin/env sh

SRC_DIR="$(
	cd -- "$(dirname "$0")" >/dev/null 2>&1
	pwd -P
)"
BASE_DIR="$(cd $SRC_DIR/../.. && pwd -P)"
BUILD_DIR="$BASE_DIR/backend/enterprise"

mkdir -p $BUILD_DIR/ciso_assistant
touch $BUILD_DIR/ciso_assistant/__init__.py

cp $SRC_DIR/ciso_assistant/* $BUILD_DIR/ciso_assistant
