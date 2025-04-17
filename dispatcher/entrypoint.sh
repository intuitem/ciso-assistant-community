#!/usr/bin/env bash
set -e

uv run dispatcher.py init-config -y
uv run dispatcher.py auth
uv run dispatcher.py consume
