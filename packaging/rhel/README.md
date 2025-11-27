# CISO Assistant - Air-Gapped RPM Package

This directory contains everything needed to build and deploy CISO Assistant as a fully self-contained RPM package for air-gapped RHEL systems.

## Overview

The RPM package includes:
- **Python 3.12** runtime with all backend dependencies
- **Node.js 22** runtime with all frontend dependencies
- **Backend** Django application (API server)
- **Huey** background task worker
- **Frontend** SvelteKit application (SSR server)
- **SQLite** database (no external database required)
- **Systemd** service files for all components

**Zero external dependencies required** - everything is bundled!

## Architecture

```
┌─────────────────────────────────────────┐
│         CISO Assistant RPM              │
├─────────────────────────────────────────┤
│  Frontend (SvelteKit/Node.js)  :3000    │
│           ↓ HTTP API calls              │
│  Backend (Django/Gunicorn)     :8000    │
│  Huey (Background Worker)               │
│  SQLite Database                        │
│                                         │
│  Bundled Runtimes:                      │
│  - Python 3.12 + virtualenv             │
│  - Node.js 22                           │
└─────────────────────────────────────────┘
```

All three services run as systemd daemons under the `ciso-assistant` user.

## Building the RPM

### Prerequisites (Build Machine)

The build machine needs internet access and these tools:

```bash
# Install build dependencies
sudo dnf install -y rpm-build rsync curl gcc make openssl-devel \
    bzip2-devel libffi-devel zlib-devel

# Install poetry (for Python dependencies)
curl -sSL https://install.python-poetry.org | python3 -

# Install pnpm (for Node.js dependencies)
npm install -g pnpm
```

### Build Process

```bash
cd packaging/rhel

# Build the RPM (this will take 15-30 minutes)
./build-rpm.sh

# The RPM will be created in RPMS/x86_64/
# Example: RPMS/x86_64/ciso-assistant-1.0.0-1.el9.x86_64.rpm
```

The build script:
1. Downloads and compiles Python 3.12 from source
2. Creates a virtualenv with all backend dependencies
3. Downloads Node.js 22 prebuilt binaries
4. Builds the frontend with all production dependencies
5. Bundles everything into a single RPM

### Build Artifacts

The resulting RPM will be approximately **300-500 MB** depending on dependencies.

## Installing on Air-Gapped Systems

### Transfer the RPM

Copy the built RPM to your air-gapped RHEL system:

```bash
# From build machine
scp RPMS/x86_64/ciso-assistant-*.rpm user@target-host:/tmp/

# Or use USB drive, CD, etc.
```

### Install the RPM

On the target RHEL system (RHEL 8, 9, or compatible):

```bash
# Install the package
sudo rpm -ivh /tmp/ciso-assistant-*.rpm

# The installer will:
# - Create /opt/ciso-assistant/ with all application files
# - Create ciso-assistant system user
# - Install systemd service files
# - Run database migrations
# - Enable services (but not start them)
```

### Post-Installation Setup

```bash
# 1. Review and update configuration
sudo vim /etc/ciso-assistant/backend.env
sudo vim /etc/ciso-assistant/frontend.env

# 2. Create administrator account
ciso-assistant-manage createsuperuser

# 3. Start services
sudo systemctl start ciso-assistant-backend
sudo systemctl start ciso-assistant-huey
sudo systemctl start ciso-assistant-frontend

# 4. Verify services are running
sudo systemctl status ciso-assistant-*
```

Or use the automated setup script:

```bash
# Run interactive post-install wizard
sudo bash /opt/ciso-assistant/post-install-setup.sh
```

## Configuration

### Backend Configuration

Edit `/etc/ciso-assistant/backend.env`:

```bash
# Application URL (update if using reverse proxy/HTTPS)
CISO_ASSISTANT_URL=https://your-domain.com

# Allowed hosts (update with your domain/IP)
ALLOWED_HOSTS=your-domain.com,192.168.1.100

# Email settings (optional)
EMAIL_HOST=smtp.company.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@company.com
EMAIL_HOST_PASSWORD=secret

# Security settings (update CSRF/CORS for your domain)
CSRF_TRUSTED_ORIGINS=https://your-domain.com
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

### Frontend Configuration

Edit `/etc/ciso-assistant/frontend.env`:

```bash
# Update if using different port or reverse proxy
ORIGIN=https://your-domain.com
PORT=3000

# Backend API connection (usually localhost)
PUBLIC_BACKEND_API_URL=http://localhost:8000/api
```

After configuration changes:

```bash
sudo systemctl restart ciso-assistant-*
```

## Service Management

### Systemd Commands

```bash
# Start all services
sudo systemctl start ciso-assistant-backend
sudo systemctl start ciso-assistant-huey
sudo systemctl start ciso-assistant-frontend

# Stop all services
sudo systemctl stop ciso-assistant-*

# Restart all services
sudo systemctl restart ciso-assistant-*

# View service status
sudo systemctl status ciso-assistant-backend
sudo systemctl status ciso-assistant-huey
sudo systemctl status ciso-assistant-frontend

# Enable services on boot (already done by installer)
sudo systemctl enable ciso-assistant-*

# View logs
sudo journalctl -u ciso-assistant-backend -f
sudo journalctl -u ciso-assistant-huey -f
sudo journalctl -u ciso-assistant-frontend -f

# View all CISO Assistant logs together
sudo journalctl -u ciso-assistant-* -f
```

### Django Management

Use the `ciso-assistant-manage` wrapper for Django management commands:

```bash
# Create superuser
ciso-assistant-manage createsuperuser

# Run migrations (usually automatic)
ciso-assistant-manage migrate

# Collect static files
ciso-assistant-manage collectstatic

# Django shell
ciso-assistant-manage shell

# Any other Django management command
ciso-assistant-manage <command> [args]
```

## File Locations

```
/opt/ciso-assistant/              # Application root
├── backend/                      # Django application
├── frontend/                     # SvelteKit application
├── venv/                         # Bundled Python virtualenv
├── node/                         # Bundled Node.js runtime
└── logs/                         # Installation logs

/etc/ciso-assistant/              # Configuration files
├── backend.env                   # Backend environment
└── frontend.env                  # Frontend environment

/var/lib/ciso-assistant/          # Data directory
├── db/                           # SQLite database
│   └── ciso-assistant.sqlite3
└── media/                        # Uploaded files

/usr/lib/systemd/system/          # Systemd services
├── ciso-assistant-backend.service
├── ciso-assistant-huey.service
└── ciso-assistant-frontend.service
```

## Accessing the Application

Once services are running:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api
- **API Documentation**: http://localhost:8000/api/schema/swagger/ (if DEBUG=True)

For production, use a reverse proxy (nginx/Apache) with HTTPS.

## Upgrading

To upgrade to a new version:

```bash
# Stop services
sudo systemctl stop ciso-assistant-*

# Install new RPM
sudo rpm -Uvh ciso-assistant-NEW-VERSION.rpm

# The upgrade will:
# - Preserve configuration files in /etc/ciso-assistant/
# - Preserve database in /var/lib/ciso-assistant/
# - Run new migrations automatically

# Start services
sudo systemctl start ciso-assistant-*
```

## Uninstalling

```bash
# Stop and remove services
sudo systemctl stop ciso-assistant-*
sudo rpm -e ciso-assistant

# Data and configuration are preserved in:
# - /var/lib/ciso-assistant/
# - /etc/ciso-assistant/

# To completely remove everything:
sudo rm -rf /opt/ciso-assistant
sudo rm -rf /var/lib/ciso-assistant
sudo rm -rf /etc/ciso-assistant
sudo userdel ciso-assistant
sudo groupdel ciso-assistant
```

## Troubleshooting

### Services won't start

```bash
# Check service status
sudo systemctl status ciso-assistant-backend -l

# View detailed logs
sudo journalctl -u ciso-assistant-backend -n 100 --no-pager

# Check configuration
sudo -u ciso-assistant /opt/ciso-assistant/venv/bin/python /opt/ciso-assistant/backend/manage.py check
```

### Permission issues

```bash
# Reset ownership
sudo chown -R ciso-assistant:ciso-assistant /opt/ciso-assistant
sudo chown -R ciso-assistant:ciso-assistant /var/lib/ciso-assistant
```

### Database issues

```bash
# Check database
sudo -u ciso-assistant sqlite3 /var/lib/ciso-assistant/db/ciso-assistant.sqlite3 ".tables"

# Run migrations manually
ciso-assistant-manage migrate
```

### Port conflicts

```bash
# Check what's using port 8000 or 3000
sudo netstat -tlnp | grep -E ':(8000|3000)'

# Update ports in configuration files
sudo vim /etc/ciso-assistant/backend.env
sudo vim /etc/ciso-assistant/frontend.env
```

## Security Considerations

### Production Deployment

For production use:

1. **Use HTTPS**: Set up nginx/Apache reverse proxy with SSL certificates
2. **Firewall**: Only expose ports 80/443, keep 8000/3000 internal
3. **SELinux**: The RPM is SELinux-aware (if enabled)
4. **Updates**: Monitor for security updates and rebuild RPM as needed
5. **Backups**: Regularly backup `/var/lib/ciso-assistant/db/`

### Example nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name ciso-assistant.company.com;

    ssl_certificate /etc/pki/tls/certs/ciso-assistant.crt;
    ssl_certificate_key /etc/pki/tls/private/ciso-assistant.key;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Support

- **GitHub**: https://github.com/intuitem/ciso-assistant-community
- **Issues**: https://github.com/intuitem/ciso-assistant-community/issues
- **Documentation**: https://github.com/intuitem/ciso-assistant-community/wiki

## License

CISO Assistant Community Edition is licensed under AGPLv3.
