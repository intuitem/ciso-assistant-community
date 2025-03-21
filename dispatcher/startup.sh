#!/usr/bin/env bash

poetry run python dispatcher.py init-config -y
poetry run python dispatcher.py auth
poetry run python dispatcher.py consume
