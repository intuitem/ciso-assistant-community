#!/usr/bin/env bash

uv run dispatcher.py init-config -y
uv run dispatcher.py auth
uv run dispatcher.py consume
