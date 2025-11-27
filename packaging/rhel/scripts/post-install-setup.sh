#!/bin/bash
# CISO Assistant Post-Installation Setup Script
# Run this after RPM installation to complete setup

set -e

echo "======================================"
echo " CISO Assistant Post-Install Setup"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    echo "Usage: sudo $0"
    exit 1
fi

# Check if services are installed
if ! systemctl list-unit-files | grep -q ciso-assistant-backend; then
    echo "ERROR: CISO Assistant services not found. Please install the RPM first."
    exit 1
fi

echo "Step 1: Configuration Review"
echo "----------------------------"
echo "Configuration files are located in /etc/ciso-assistant/"
echo ""
echo "Backend: /etc/ciso-assistant/backend.env"
echo "Frontend: /etc/ciso-assistant/frontend.env"
echo ""
read -p "Have you reviewed and updated the configuration? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please review configuration files before continuing."
    exit 1
fi

echo ""
echo "Step 2: Database Initialization"
echo "----------------------------"
echo "Running Django migrations..."
cd /opt/ciso-assistant/backend
sudo -u ciso-assistant /opt/ciso-assistant/venv/bin/python manage.py migrate

echo ""
echo "Step 3: Create Superuser"
echo "----------------------------"
echo "You will now create an administrator account."
sudo -u ciso-assistant /opt/ciso-assistant/venv/bin/python manage.py createsuperuser

echo ""
echo "Step 4: Start Services"
echo "----------------------------"
read -p "Start CISO Assistant services now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl start ciso-assistant-backend
    systemctl start ciso-assistant-huey
    systemctl start ciso-assistant-frontend

    echo ""
    echo "Checking service status..."
    sleep 3
    systemctl status ciso-assistant-backend --no-pager || true
    systemctl status ciso-assistant-huey --no-pager || true
    systemctl status ciso-assistant-frontend --no-pager || true
fi

echo ""
echo "======================================"
echo " Setup Complete!"
echo "======================================"
echo ""
echo "CISO Assistant is now running:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:8000/api"
echo ""
echo "Useful commands:"
echo "  - View logs: journalctl -u ciso-assistant-backend -f"
echo "  - Restart services: systemctl restart ciso-assistant-*"
echo "  - Stop services: systemctl stop ciso-assistant-*"
echo "  - Django management: ciso-assistant-manage <command>"
echo ""
echo "Documentation: https://github.com/intuitem/ciso-assistant-community"
echo ""
