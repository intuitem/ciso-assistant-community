# Offline Deployment Guide

This guide explains how to prepare CISO Assistant for production deployment on an air-gapped server (without internet access).

## Overview

You'll use an **online workstation** to download dependencies and build the application, then transfer everything to the **offline server**.

**Assumption:** The online workstation and offline server have the same architecture and OS.

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

# Install dependencies
poetry install --only main
```

### Build Frontend

```bash
cd ../frontend

# Install dependencies
pnpm install

# Build for production
PUBLIC_BACKEND_API_URL=https://your-domain/api pnpm run build

# Prune to production dependencies only
pnpm prune --prod
```

## Step 2: Transfer to Offline Server

Transfer the entire `ciso-assistant-community` directory to the offline server, including:
- `backend/venv/` directory (complete virtual environment)
- `frontend/build/` directory (built frontend for SSR)
- `frontend/server/` directory (Node.js server)
- `frontend/node_modules/` directory (production dependencies)
- `frontend/package.json`
- All source code

## Step 3: Deploy on Offline Server

### Configure Environment

Create `backend/.env` file:

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

# Gunicorn configuration (optional)
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=120
```

### Create Superuser

After the first startup, create a superuser account:

```bash
cd /path/to/ciso-assistant-community/backend
source venv/bin/activate
python manage.py createsuperuser
```

### Set Up Gunicorn Service

Create `/etc/systemd/system/ciso-assistant.service`:

```ini
[Unit]
Description=CISO Assistant Gunicorn Service
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

**Note:** The `startup.sh` script automatically:
- Waits for database to be ready
- Runs migrations
- Loads security frameworks with `storelibraries`
- Starts gunicorn with optimal settings

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
Environment="ORIGIN=https://your-domain"
Environment="PUBLIC_BACKEND_API_URL=https://your-domain/api"
ExecStart=/usr/bin/node server

[Install]
WantedBy=multi-user.target
```

### Start Services

```bash
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable ciso-assistant
sudo systemctl enable ciso-assistant-huey
sudo systemctl enable ciso-assistant-frontend
sudo systemctl start ciso-assistant
sudo systemctl start ciso-assistant-huey
sudo systemctl start ciso-assistant-frontend

# Check status
sudo systemctl status ciso-assistant
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
    ciso-assistant:
      rule: "Host(`your-domain`)"
      service: ciso-assistant
      tls:
        certResolver: letsencrypt
      middlewares:
        - ciso-assistant-headers

  services:
    ciso-assistant:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:8000"

  middlewares:
    ciso-assistant-headers:
      headers:
        customRequestHeaders:
          X-Forwarded-Proto: "https"
```

Configure static file serving separately or use a file server alongside Traefik.

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

## Post-Deployment

1. Access the application at `https://your-domain`
2. Log in with the superuser credentials
3. Configure application settings
4. Import security frameworks from the library

## Monitoring

```bash
# View logs
sudo journalctl -u ciso-assistant -f
sudo journalctl -u ciso-assistant-huey -f
sudo journalctl -u ciso-assistant-frontend -f

# Check service status
sudo systemctl status ciso-assistant
sudo systemctl status ciso-assistant-huey
sudo systemctl status ciso-assistant-frontend
```

## Troubleshooting

- Ensure Python 3.12+ and Node 22+ are installed
- Verify yaml-cpp library is installed
- Check all services are running: `sudo systemctl status ciso-assistant ciso-assistant-huey ciso-assistant-frontend`
- Review logs for errors:
  - Backend: `sudo journalctl -u ciso-assistant -n 100`
  - Frontend: `sudo journalctl -u ciso-assistant-frontend -n 100`
  - Huey: `sudo journalctl -u ciso-assistant-huey -n 100`
- Ensure `.env` file has correct permissions (600)
- Verify `ORIGIN` and `PUBLIC_BACKEND_API_URL` are correctly set in frontend service

## Updates

To update an offline deployment:

1. On online workstation: Pull latest code, rebuild venv and frontend (including `pnpm prune --prod`)
2. Transfer updated files to offline server
3. Restart services: `sudo systemctl restart ciso-assistant ciso-assistant-huey ciso-assistant-frontend`

**Note:** The `startup.sh` script automatically runs migrations on startup, so no manual migration step is needed.
