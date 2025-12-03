# Offline Deployment Guide

This guide explains how to prepare CISO Assistant for production deployment on an air-gapped server (without internet access).

## Overview

You'll use an **online workstation** to download dependencies and build the application, then transfer everything to the **offline server**.

**Assumption:** The online workstation and offline server have the same architecture and OS.

**Note:** This guide covers both Community and Enterprise editions. Enterprise-specific steps are clearly marked.

## Prerequisites

**On the online workstation:**
- Internet connection
- Git
- Python 3.12+ with poetry 2.0+
- Node 22+ with pnpm 9.0+
- yaml-cpp library

**On the offline server:**
- Python 3.12+
- Node 22+
- yaml-cpp library
- Reverse proxy (Caddy or Traefik recommended)
- **Enterprise only:** Additional system packages: `build-essential`, `python3-dev`, `python3-numpy`, `libjpeg-dev`, `libmagic1`

## Step 1: Prepare on Online Workstation

### Clone the Repository

```bash
git clone https://github.com/intuitem/ciso-assistant-community.git
cd ciso-assistant-community
```

### Prepare Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install poetry in the venv (required by startup.sh)
pip install poetry

# Install dependencies
poetry install --only main
```

**For Enterprise Edition:**

After installing backend dependencies, copy the enterprise core module:

```bash
# From the repository root
cp -r enterprise/backend/enterprise_core backend/
```

### Build Frontend

```bash
cd frontend

# Install dependencies
pnpm install

# Build for production
NODE_OPTIONS="--max-old-space-size=8192" pnpm run build

# Prune to production dependencies only
pnpm prune
```

**Note:** `PUBLIC_BACKEND_API_URL` is not required during build because the frontend uses SvelteKit's dynamic environment variables, which are read at runtime. You'll configure this when setting up the frontend service on the offline server.

**For Enterprise Edition:**

Before building, overlay the enterprise frontend files:

```bash
# From the repository root
cp -r enterprise/frontend/* frontend/
# Then proceed with pnpm install and build
```

## Step 2: Transfer to Offline Server

Transfer the following to the offline server:
- `backend/` directory (including `venv/` with complete virtual environment)
- `frontend/` directory (including `build/`, `server/`, `node_modules/`, and `package.json`)

## Step 3: Deploy on Offline Server

### Configure Environment

Create `backend/.env` file:

**For Community Edition:**

```bash
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=your-secret-key
CISO_ASSISTANT_URL=https://your-domain
ALLOWED_HOSTS=your-domain,localhost

# Email configuration
EMAIL_HOST=your-smtp-host
EMAIL_PORT=587
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-password

# PostgreSQL configuration (optional, defaults to SQLite)
# POSTGRES_NAME=ciso-assistant
# POSTGRES_USER=ciso-assistant-user
# POSTGRES_PASSWORD=your-password
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432

# Gunicorn configuration (optional)
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=120
```

**For Enterprise Edition:**

Add these additional variables to the `.env` file:

```bash
# Enterprise settings
DJANGO_SETTINGS_MODULE=enterprise_core.settings

# License configuration
LICENSE_SEATS=50
LICENSE_EXPIRATION=2025-12-31

# S3 Storage (optional)
# USE_S3=True
# AWS_ACCESS_KEY_ID=your-access-key
# AWS_SECRET_ACCESS_KEY=your-secret-key
# AWS_STORAGE_BUCKET_NAME=ciso-assistant-bucket
# AWS_S3_ENDPOINT_URL=https://s3.your-domain.com

# Email rescue (backup email server)
# EMAIL_HOST_RESCUE=your-backup-smtp-host
# EMAIL_PORT_RESCUE=587
# EMAIL_HOST_USER_RESCUE=your-backup-email
# EMAIL_HOST_PASSWORD_RESCUE=your-backup-password
# EMAIL_USE_TLS_RESCUE=True

# Audit log configuration
AUDITLOG_RETENTION_DAYS=90
AUDITLOG_MAX_RECORDS=50000

# Webhook configuration
# WEBHOOK_ALLOW_PRIVATE_IPS=False

# Logging
# LOG_LEVEL=INFO
# LOG_FORMAT=json
# LOG_OUTFILE=True
```

### Initial Setup

Before starting the services, run migrations and create a superuser account:

```bash
cd /path/to/ciso-assistant-community/backend
source venv/bin/activate

# Run database migrations
python manage.py migrate

# Create superuser account
python manage.py createsuperuser
```

### Set Up Backend Service

**Note:** In the following service configurations, update these values to match your offline server setup:
- Replace `/path/to/ciso-assistant-community` with the actual installation path
- Replace `your-domain` with your actual domain name
- Replace `ciso-assistant` user/group with your actual system user
- Update binary paths (e.g., `/usr/bin/node`, `/usr/bin/bash`) if they're located elsewhere on your system

Create `/etc/systemd/system/ciso-assistant-backend.service`:

```ini
[Unit]
Description=CISO Assistant Backend Service
After=network.target

[Service]
Type=exec
User=ciso-assistant
Group=ciso-assistant
WorkingDirectory=/path/to/ciso-assistant-community/backend
Environment="PATH=/path/to/ciso-assistant-community/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/path/to/ciso-assistant-community/backend/.env
ExecStart=/usr/bin/bash startup.sh

[Install]
WantedBy=multi-user.target
```

**Note:** The `startup.sh` script automatically handles database migrations, library loading, and starts Gunicorn.

### Set Up Huey Service

Create `/etc/systemd/system/ciso-assistant-huey.service`:

```ini
[Unit]
Description=CISO Assistant Huey Background Tasks
After=network.target

[Service]
Type=simple
User=ciso-assistant
Group=ciso-assistant
WorkingDirectory=/path/to/ciso-assistant-community/backend
Environment="PATH=/path/to/ciso-assistant-community/backend/venv/bin"
EnvironmentFile=/path/to/ciso-assistant-community/backend/.env
ExecStart=/path/to/ciso-assistant-community/backend/venv/bin/python \
    manage.py run_huey -w 2 -k process

[Install]
WantedBy=multi-user.target
```

### Set Up Frontend Service

Create `/etc/systemd/system/ciso-assistant-frontend.service`:

```ini
[Unit]
Description=CISO Assistant Frontend (SvelteKit SSR)
After=network.target

[Service]
Type=simple
User=ciso-assistant
Group=ciso-assistant
WorkingDirectory=/path/to/ciso-assistant-community/frontend
Environment="NODE_ENV=production"
Environment="BODY_SIZE_LIMIT=25000000"
Environment="ORIGIN=http://localhost:3000"
Environment="PUBLIC_BACKEND_API_URL=http://localhost:8000/api"
ExecStart=/usr/bin/node server

[Install]
WantedBy=multi-user.target
```

**Important environment variables:**
- `ORIGIN`: Must match the URL users will access in their browser. The default is `http://localhost:3000`. For production with a reverse proxy, change this to your actual domain (e.g., `https://your-domain` or `https://your-domain:8443`). Pay attention to the protocol (http/https) and port.
- `PUBLIC_BACKEND_API_URL`: Points to the backend API. Use `http://localhost:8000/api` for internal communication between frontend and backend services.

### Start Services

```bash
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable ciso-assistant-backend
sudo systemctl enable ciso-assistant-huey
sudo systemctl enable ciso-assistant-frontend
sudo systemctl start ciso-assistant-backend
sudo systemctl start ciso-assistant-huey
sudo systemctl start ciso-assistant-frontend

# Check status
sudo systemctl status ciso-assistant-backend
sudo systemctl status ciso-assistant-huey
sudo systemctl status ciso-assistant-frontend
```

### Configure Reverse Proxy

**Option 1: Caddy (Recommended)**

Create `/etc/caddy/Caddyfile`:

```caddy
your-domain {
    # Proxy API requests to backend
    reverse_proxy /api/* 127.0.0.1:8000

    # Proxy all other requests to frontend (SvelteKit SSR)
    reverse_proxy 127.0.0.1:3000

    # Request size limit
    request_body {
        max_size 100MB
    }
}
```

Reload Caddy:
```bash
sudo systemctl reload caddy
```

**Option 2: Traefik**

Create `docker-compose.yml` for Traefik or configure via static/dynamic configuration files. Example dynamic configuration:

```yaml
http:
  routers:
    ciso-assistant-api:
      rule: "Host(`your-domain`) && PathPrefix(`/api`)"
      service: ciso-assistant-backend
      priority: 10
      tls:
        certResolver: letsencrypt

    ciso-assistant-frontend:
      rule: "Host(`your-domain`)"
      service: ciso-assistant-frontend
      tls:
        certResolver: letsencrypt

  services:
    ciso-assistant-backend:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:8000"

    ciso-assistant-frontend:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:3000"
```

**Option 3: Apache**

Create `/etc/apache2/sites-available/ciso-assistant.conf`:

```apache
<VirtualHost *:80>
    ServerName your-domain
    Redirect permanent / https://your-domain/
</VirtualHost>

<VirtualHost *:443>
    ServerName your-domain

    SSLEngine on
    SSLCertificateFile /path/to/cert.pem
    SSLCertificateKeyFile /path/to/key.pem

    # Proxy API requests to backend
    ProxyPreserveHost On
    ProxyPass /api/ http://127.0.0.1:8000/api/
    ProxyPassReverse /api/ http://127.0.0.1:8000/api/

    # Proxy all other requests to frontend (SvelteKit SSR)
    ProxyPass / http://127.0.0.1:3000/
    ProxyPassReverse / http://127.0.0.1:3000/

    # Request size limit
    LimitRequestBody 104857600

    # Timeouts
    ProxyTimeout 120

    ErrorLog ${APACHE_LOG_DIR}/ciso-assistant-error.log
    CustomLog ${APACHE_LOG_DIR}/ciso-assistant-access.log combined
</VirtualHost>
```

Enable required modules and site:
```bash
sudo a2enmod ssl proxy proxy_http headers
sudo a2ensite ciso-assistant
sudo apache2ctl configtest
sudo systemctl reload apache2
```

**Important:** After configuring your reverse proxy with your actual domain, update the `ORIGIN` environment variable in the frontend service configuration (`/etc/systemd/system/ciso-assistant-frontend.service`) to match your domain (e.g., `https://your-domain`), then restart the frontend service: `sudo systemctl restart ciso-assistant-frontend`.

## Post-Deployment

1. Access the application at `https://your-domain`
2. Log in with the superuser credentials
3. Configure application settings
4. Import security frameworks from the library

## Monitoring

```bash
# View logs
sudo journalctl -u ciso-assistant-backend -f
sudo journalctl -u ciso-assistant-huey -f
sudo journalctl -u ciso-assistant-frontend -f

# Check service status
sudo systemctl status ciso-assistant-backend
sudo systemctl status ciso-assistant-huey
sudo systemctl status ciso-assistant-frontend
```

## Troubleshooting

- Ensure Python 3.12+ and Node 22+ are installed
- Verify yaml-cpp library is installed
- Check all services are running: `sudo systemctl status ciso-assistant-backend ciso-assistant-huey ciso-assistant-frontend`
- Review logs for errors:
  - Backend: `sudo journalctl -u ciso-assistant-backend -n 100`
  - Frontend: `sudo journalctl -u ciso-assistant-frontend -n 100`
  - Huey: `sudo journalctl -u ciso-assistant-huey -n 100`
- Ensure `.env` file has correct permissions (600)
- Verify `ORIGIN` and `PUBLIC_BACKEND_API_URL` are correctly set in frontend service

## Updates

To update an offline deployment:

1. On online workstation: Pull latest code, rebuild venv and frontend (including `pnpm prune`)
2. **Enterprise only:** Re-copy enterprise modules (`enterprise_core` and enterprise frontend files)
3. Transfer updated files to offline server
4. Restart services: `sudo systemctl restart ciso-assistant-backend ciso-assistant-huey ciso-assistant-frontend`

**Important:**
- The `startup.sh` script automatically runs migrations on startup, so no manual migration step is needed.
- **⚠️ WARNING:** Always preserve and backup the `backend/db/` folder on the offline server before updating. This folder contains:
  - The SQLite database (if not using PostgreSQL)
  - Uploaded evidence files and attachments
  - Other critical application data

  Never overwrite this folder when transferring updated files.
