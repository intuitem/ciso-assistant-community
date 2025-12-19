# RPM Build & Deployment Checklist

## Pre-Build Checklist (Build Machine)

- [ ] Build machine has internet access
- [ ] RHEL/Rocky/AlmaLinux 8 or 9 installed
- [ ] Build tools installed: `rpm-build rsync curl gcc make openssl-devel bzip2-devel libffi-devel zlib-devel`
- [ ] Poetry installed for Python dependency management
- [ ] pnpm installed for Node.js dependency management
- [ ] Git repository is clean (committed changes)
- [ ] Version number updated if needed (set VERSION env var)

## Build Process

- [ ] Run `./build-rpm.sh` from `packaging/rhel/` directory
- [ ] Build completes without errors (~15-30 minutes)
- [ ] RPM file created in `RPMS/x86_64/`
- [ ] RPM size is reasonable (300-500 MB expected)
- [ ] Verify RPM contents: `rpm -qlp RPMS/x86_64/ciso-assistant-*.rpm`

## Pre-Deployment Checklist (Target System)

- [ ] Target system is RHEL 8, 9, or compatible (Rocky/Alma)
- [ ] Target system is x86_64 architecture
- [ ] System has at least 2 GB RAM
- [ ] System has at least 2 GB free disk space
- [ ] No conflicting services on ports 3000 or 8000
- [ ] Firewall rules planned (if applicable)
- [ ] SSL certificates obtained (if using HTTPS/reverse proxy)

## Transfer to Air-Gapped System

- [ ] RPM file transferred to target system (USB/network/etc.)
- [ ] File integrity verified (checksum)
- [ ] Transfer method documented for future updates

## Installation on Target System

- [ ] RPM installed: `sudo rpm -ivh ciso-assistant-*.rpm`
- [ ] Installation completes without errors
- [ ] System user `ciso-assistant` created
- [ ] Files present in `/opt/ciso-assistant/`
- [ ] Configuration files in `/etc/ciso-assistant/`
- [ ] Systemd services registered

## Post-Installation Configuration

- [ ] Backend configuration reviewed (`/etc/ciso-assistant/backend.env`)
  - [ ] `ALLOWED_HOSTS` updated with actual hostname/IP
  - [ ] `CISO_ASSISTANT_URL` updated for production URL
  - [ ] `CSRF_TRUSTED_ORIGINS` updated
  - [ ] `CORS_ALLOWED_ORIGINS` updated
  - [ ] Email settings configured (if needed)
- [ ] Frontend configuration reviewed (`/etc/ciso-assistant/frontend.env`)
  - [ ] `ORIGIN` updated for production URL
  - [ ] `PUBLIC_BACKEND_API_URL` verified (usually localhost:8000)
- [ ] Permissions verified: `ls -la /opt/ciso-assistant /var/lib/ciso-assistant /etc/ciso-assistant`

## Initial Setup

- [ ] Superuser created: `ciso-assistant-manage createsuperuser`
- [ ] Services started:
  - [ ] `sudo systemctl start ciso-assistant-backend`
  - [ ] `sudo systemctl start ciso-assistant-huey`
  - [ ] `sudo systemctl start ciso-assistant-frontend`
- [ ] All services running: `sudo systemctl status ciso-assistant-*`
- [ ] No errors in logs: `sudo journalctl -u ciso-assistant-* -n 100`

## Verification Tests

- [ ] Frontend accessible at http://localhost:3000
- [ ] Login page loads correctly
- [ ] Can log in with superuser credentials
- [ ] Backend API responding at http://localhost:8000/api
- [ ] Background tasks processing (check Huey logs)
- [ ] Can create a test project/assessment
- [ ] Can upload a file (tests media directory)

## Production Hardening (If Applicable)

- [ ] Reverse proxy configured (nginx/Apache)
  - [ ] HTTPS/SSL configured
  - [ ] Headers configured (X-Forwarded-For, etc.)
  - [ ] Timeouts set appropriately
- [ ] Firewall configured
  - [ ] Port 3000/8000 blocked from external access
  - [ ] Only 80/443 exposed (reverse proxy)
- [ ] SELinux configured (if enabled)
- [ ] Services enabled on boot: `sudo systemctl enable ciso-assistant-*`
- [ ] Monitoring configured
  - [ ] Log aggregation
  - [ ] Service health checks
  - [ ] Disk space monitoring

## Backup Configuration

- [ ] Backup strategy documented
- [ ] Database backup script created
- [ ] Media files backup configured
- [ ] Backup restoration tested
- [ ] Backup schedule configured (cron/systemd timer)

## Documentation

- [ ] Installation notes documented
- [ ] Custom configuration documented
- [ ] Administrator contacts documented
- [ ] Backup/restore procedures documented
- [ ] Troubleshooting notes captured

## Training

- [ ] System administrators trained on:
  - [ ] Service management (start/stop/restart)
  - [ ] Log viewing
  - [ ] User management
  - [ ] Backup/restore
  - [ ] Troubleshooting basics
- [ ] End users trained on application usage

## Handoff

- [ ] System handed over to operations team
- [ ] Documentation provided
- [ ] Support contacts shared
- [ ] Escalation procedures defined
- [ ] Update/maintenance schedule planned

## Post-Deployment Monitoring (First Week)

- [ ] Day 1: Verify all services running
- [ ] Day 1: Check logs for errors
- [ ] Day 2: Verify user access and usage
- [ ] Day 3: Check disk space and resource usage
- [ ] Day 7: First backup completed and verified
- [ ] Day 7: Performance review

## Notes

Use this space to document any custom configurations or issues encountered:

```
Date: _______________
Deployed by: _______________
System: _______________
Version: _______________

Custom configurations:
-
-
-

Issues encountered:
-
-
-

```
