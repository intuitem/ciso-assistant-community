# CISO Assistant - Quick Start Guide

## Installation (5 minutes)

```bash
# 1. Install RPM
sudo rpm -ivh ciso-assistant-*.rpm

# 2. Create admin user
ciso-assistant-manage createsuperuser

# 3. Start services
sudo systemctl start ciso-assistant-backend ciso-assistant-huey ciso-assistant-frontend

# 4. Access application
# Open browser: http://localhost:3000
```

## Daily Operations

### Start/Stop Services

```bash
# Start
sudo systemctl start ciso-assistant-*

# Stop
sudo systemctl stop ciso-assistant-*

# Restart
sudo systemctl restart ciso-assistant-*

# Status
sudo systemctl status ciso-assistant-*
```

### View Logs

```bash
# All services
sudo journalctl -u ciso-assistant-* -f

# Specific service
sudo journalctl -u ciso-assistant-backend -f
sudo journalctl -u ciso-assistant-huey -f
sudo journalctl -u ciso-assistant-frontend -f
```

### User Management

```bash
# Create superuser
ciso-assistant-manage createsuperuser

# Django shell (for advanced user management)
ciso-assistant-manage shell
```

### Backup & Restore

```bash
# Backup database
sudo cp /var/lib/ciso-assistant/db/ciso-assistant.sqlite3 \
    /backup/ciso-assistant-$(date +%Y%m%d).sqlite3

# Backup media files
sudo tar -czf /backup/media-$(date +%Y%m%d).tar.gz \
    /var/lib/ciso-assistant/media/

# Restore database
sudo systemctl stop ciso-assistant-*
sudo cp /backup/ciso-assistant-20241127.sqlite3 \
    /var/lib/ciso-assistant/db/ciso-assistant.sqlite3
sudo chown ciso-assistant:ciso-assistant \
    /var/lib/ciso-assistant/db/ciso-assistant.sqlite3
sudo systemctl start ciso-assistant-*
```

### Updates

```bash
# Stop services
sudo systemctl stop ciso-assistant-*

# Update RPM
sudo rpm -Uvh ciso-assistant-NEW-VERSION.rpm

# Start services (migrations run automatically)
sudo systemctl start ciso-assistant-*
```

## Configuration Files

```bash
# Backend settings
sudo vim /etc/ciso-assistant/backend.env

# Frontend settings
sudo vim /etc/ciso-assistant/frontend.env

# After changes, restart services
sudo systemctl restart ciso-assistant-*
```

## Common Issues

### Services won't start
```bash
# Check logs
sudo journalctl -u ciso-assistant-backend -n 50

# Verify configuration
ciso-assistant-manage check
```

### Can't access web interface
```bash
# Check if services are running
sudo systemctl status ciso-assistant-*

# Check ports
sudo netstat -tlnp | grep -E ':(8000|3000)'

# Check firewall
sudo firewall-cmd --list-all
```

### Permission denied errors
```bash
# Reset ownership
sudo chown -R ciso-assistant:ciso-assistant /opt/ciso-assistant
sudo chown -R ciso-assistant:ciso-assistant /var/lib/ciso-assistant
```

## File Locations

| Path | Description |
|------|-------------|
| `/opt/ciso-assistant/` | Application files |
| `/etc/ciso-assistant/` | Configuration |
| `/var/lib/ciso-assistant/db/` | Database |
| `/var/lib/ciso-assistant/media/` | Uploads |

## Ports

| Port | Service | Internal/External |
|------|---------|-------------------|
| 3000 | Frontend | External (user-facing) |
| 8000 | Backend API | Internal (localhost only) |

## Support

- Documentation: See `README.md` in this directory
- GitHub: https://github.com/intuitem/ciso-assistant-community
- Issues: Report at GitHub Issues
