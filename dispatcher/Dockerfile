FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_IN_PROJECT=1 \
  POETRY_VIRTUALENVS_CREATE=1 \
  POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /code

RUN apt-get update && apt-get install -y \
  libyaml-cpp-dev \
  libffi-dev \
  libglib2.0-0 \
  pango-1.0 \
  libcairo2 \
  locales \
  tzdata \
  zlib1g-dev \
  && apt-get clean \
  && pip install --no-cache-dir --upgrade pip poetry==2.0.1

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root \
  && rm -rf $POETRY_CACHE_DIR

#watch out for local files during dev and maintenance of .dockerignore
COPY . .

EXPOSE 8000
ENTRYPOINT ["poetry", "run", "bash", "startup.sh"]
