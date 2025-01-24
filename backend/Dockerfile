FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /code

COPY pyproject.toml poetry.lock ./

RUN apt-get update && apt-get install -y \
    libyaml-cpp-dev \
    libffi-dev \
    libglib2.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    locales \
    tzdata \
    gettext \
    fontconfig \
    fonts-freefont-ttf \
    zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && locale-gen en_US.UTF-8 \
    && pip install --no-cache-dir --upgrade pip poetry==2.0.1 \
    && poetry install --no-root \
    && rm -rf $POETRY_CACHE_DIR

COPY . .

EXPOSE 8000
ENTRYPOINT ["poetry", "run", "bash", "startup.sh"]
