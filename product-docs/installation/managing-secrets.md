---
description: >-
  This guide covers how to keep sensitive configuration (database credentials,
  mailer passwords, API keys) out of your docker-compose.yml.
---

# Managing Secrets

### 1. The `.env` File

Docker Compose automatically loads variables from a `.env` file located next to `docker-compose.yml`. This is the recommended approach for all secrets.

#### Create the `.env` file

```dotenv
# .env

# ── Postgres ───────────────────────────
POSTGRES_NAME=ciso_assistant
POSTGRES_USER=ciso_assistant
POSTGRES_PASSWORD=change-me-to-something-strong

# ── Django / Backend ───────────────────
DJANGO_DEBUG=False
CISO_ASSISTANT_URL=https://localhost:8443
ALLOWED_HOSTS=backend,localhost
CISO_SUPERUSER_EMAIL=admin@example.com

# ── Mailer ─────────────────────────────
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=notifications@example.com
EMAIL_HOST_PASSWORD=smtp-secret-password
DEFAULT_FROM_EMAIL=ciso-assistant@example.com

# ── Rescue Mailer (optional) ──────────
# EMAIL_HOST_RESCUE=smtp2.example.com
# EMAIL_PORT_RESCUE=587
# EMAIL_HOST_USER_RESCUE=rescue@example.com
# EMAIL_HOST_PASSWORD_RESCUE=rescue-secret
# EMAIL_USE_TLS_RESCUE=True

# ── S3 Storage (optional) ─────────────
# USE_S3=True
# AWS_ACCESS_KEY_ID=AKIA...
# AWS_SECRET_ACCESS_KEY=wJal...
# AWS_STORAGE_BUCKET_NAME=my-bucket
# AWS_S3_ENDPOINT_URL=https://s3.eu-west-1.amazonaws.com
```

#### Reference variables in `docker-compose.yml`

Replace every hardcoded value with a `${VARIABLE}` reference:

```yaml
services:
  backend:
    container_name: backend
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    depends_on:
      - postgres
    environment:
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - CISO_ASSISTANT_URL=${CISO_ASSISTANT_URL}
      - DJANGO_DEBUG=${DJANGO_DEBUG}
      - POSTGRES_NAME=${POSTGRES_NAME}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - DB_HOST=postgres
      - EMAIL_HOST=${EMAIL_HOST}
      - EMAIL_PORT=${EMAIL_PORT}
      - EMAIL_USE_TLS=${EMAIL_USE_TLS}
      - EMAIL_HOST_USER=${EMAIL_HOST_USER}
      - EMAIL_HOST_PASSWORD=${EMAIL_HOST_PASSWORD}
      - DEFAULT_FROM_EMAIL=${DEFAULT_FROM_EMAIL}
      - CISO_SUPERUSER_EMAIL=${CISO_SUPERUSER_EMAIL}
    volumes:
      - ./db:/code/db

  huey:
    container_name: huey
    build:
      context: ./backend
      dockerfile: Dockerfile
    depends_on:
      - backend
    restart: always
    environment:
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - CISO_ASSISTANT_URL=${CISO_ASSISTANT_URL}
      - DJANGO_DEBUG=False
      - POSTGRES_NAME=${POSTGRES_NAME}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - DB_HOST=postgres
    volumes:
      - ./db:/code/db
    entrypoint:
      - /bin/sh
      - -c
      - |
        poetry run python manage.py run_huey -w 2 --scheduler-interval 60

  frontend:
    container_name: frontend
    environment:
      - PUBLIC_BACKEND_API_URL=http://backend:8000/api
      - PROTOCOL_HEADER=x-forwarded-proto
      - HOST_HEADER=x-forwarded-host
    build:
      context: ./frontend
      dockerfile: Dockerfile
    depends_on:
      - backend

  postgres:
    container_name: postgres
    image: postgres:16
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_NAME}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./db/pg:/var/lib/postgresql/data

  caddy:
    container_name: caddy
    image: caddy:2.10.0
    restart: unless-stopped
    ports:
      - 8443:8443
    command:
      - caddy
      - reverse-proxy
      - --from
      - https://localhost:8443
      - --to
      - frontend:3000
    volumes:
      - ./db:/data
```

> **Tip — DRY with YAML anchors:** Since `backend` and `huey` share most variables, you can use extension fields to avoid repetition:
>
> ```yaml
> x-common-env: &common-env
>   ALLOWED_HOSTS: ${ALLOWED_HOSTS}
>   CISO_ASSISTANT_URL: ${CISO_ASSISTANT_URL}
>   POSTGRES_NAME: ${POSTGRES_NAME}
>   POSTGRES_USER: ${POSTGRES_USER}
>   POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
>   DB_HOST: postgres
>
> services:
>   backend:
>     environment:
>       <<: *common-env
>       DJANGO_DEBUG: ${DJANGO_DEBUG}
>       EMAIL_HOST: ${EMAIL_HOST}
>       # ... other backend-specific vars
>
>   huey:
>     environment:
>       <<: *common-env
>       DJANGO_DEBUG: "False"
> ```

#### Protect the file

```bash
chmod 600 .env
```

***

### 2. Per-Environment Compose Overrides

Use override files to separate dev and production configurations without touching the base file:

```
docker-compose.yml              # base (references ${VARIABLES}, no secrets)
docker-compose.override.yml     # local dev defaults  (loaded automatically)
docker-compose.prod.yml         # production overrides (git-ignored)
```

```bash
# Dev — override is loaded automatically
docker compose up

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Each environment can point to its own `.env` file:

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d
```

This lets you commit safe dev defaults while keeping production secrets in a separate file.
