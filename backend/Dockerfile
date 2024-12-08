# syntax=docker/dockerfile:1
# Based on https://docs.docker.com/samples/django/
FROM python:3.11-alpine

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set working directory
WORKDIR /code

# Install system dependencies
RUN apk update && apk add --no-cache \
    bash \
    yaml-cpp \
    py3-cffi \
    libc-dev \
    libffi-dev \
    gcc \
    python3-dev \
    glib \
    pango \
    cairo \
    musl \
    musl-utils \
    musl-locales \
    tzdata \
    gettext \
    fontconfig \
    ttf-freefont \
    font-noto \
    terminus-font \
    file-dev \
    build-base \
    freetype-dev \
    libpng-dev \
    openblas-dev \
    cmake \
    g++ \
    libstdc++

# Copy project files
COPY . /code/
COPY pyproject.toml poetry.lock* startup.sh /code/

# Install Poetry and project dependencies
RUN pip install --upgrade pip && \
    pip install poetry==1.8.3 && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi && \
    rm -rf $POETRY_CACHE_DIR

# Set executable permissions for startup script
RUN chmod +x /code/startup.sh

# Expose port
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["poetry", "run", "bash", "startup.sh"]
