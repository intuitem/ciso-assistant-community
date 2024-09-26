# syntax=docker/dockerfile:1
# Based on https://docs.docker.com/samples/django/

FROM python:3.11-alpine
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

ENV DJANGO_SETTINGS_MODULE=enterprise_core.settings

WORKDIR /code

# Configure locales
RUN apk update
RUN apk add --no-cache bash yaml-cpp
RUN apk add --no-cache py3-cffi libc-dev libffi-dev gcc python3-dev glib pango cairo
RUN apk add --no-cache musl musl-utils musl-locales tzdata lang
RUN apk add --no-cache gettext fontconfig ttf-freefont font-noto terminus-font
RUN apk add --no-cache file-dev gcc

COPY backend /code/
COPY enterprise/backend/enterprise_core /code/enterprise_core
COPY backend/startup.sh /code/
COPY backend/pyproject.toml /code/
COPY backend/poetry.lock /code/

RUN pip install --upgrade pip && \
    pip install poetry==1.8.3

RUN poetry install
RUN rm -rf $POETRY_CACHE_DIR

ENTRYPOINT ["poetry", "run",  "bash", "startup.sh"]
EXPOSE 8000
