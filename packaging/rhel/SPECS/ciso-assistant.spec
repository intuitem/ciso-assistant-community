%define _build_id_links none
%define debug_package %{nil}
%define __os_install_post %{nil}

Name:           ciso-assistant
Version:        %{_version}
Release:        1%{?dist}
Summary:        CISO Assistant - Cybersecurity GRC Platform
License:        AGPLv3
URL:            https://github.com/intuitem/ciso-assistant-community
BuildArch:      x86_64

Requires:       systemd

%description
CISO Assistant is an open-source cybersecurity GRC (Governance, Risk, and
Compliance) platform that helps organizations manage their security posture,
compliance requirements, and risk assessments.

This package includes all necessary runtimes (Python, Node.js) and dependencies
for completely air-gapped deployment on RHEL systems.

%prep
# No prep needed - files are staged by build script

%build
# No build needed - binaries are pre-compiled

%install
rm -rf %{buildroot}

# Create directory structure
mkdir -p %{buildroot}/opt/ciso-assistant/{backend,frontend,venv,node,logs}
mkdir -p %{buildroot}/etc/ciso-assistant
mkdir -p %{buildroot}%{_unitdir}
mkdir -p %{buildroot}/var/lib/ciso-assistant/{db,media}
mkdir -p %{buildroot}%{_bindir}

# Copy application files
cp -r %{_sourcedir}/backend/* %{buildroot}/opt/ciso-assistant/backend/
cp -r %{_sourcedir}/frontend/* %{buildroot}/opt/ciso-assistant/frontend/
cp -r %{_sourcedir}/venv/* %{buildroot}/opt/ciso-assistant/venv/
cp -r %{_sourcedir}/node/* %{buildroot}/opt/ciso-assistant/node/

# Copy configuration templates
cp %{_sourcedir}/templates/backend.env %{buildroot}/etc/ciso-assistant/backend.env
cp %{_sourcedir}/templates/frontend.env %{buildroot}/etc/ciso-assistant/frontend.env

# Copy systemd service files
cp %{_sourcedir}/systemd/ciso-assistant-backend.service %{buildroot}%{_unitdir}/
cp %{_sourcedir}/systemd/ciso-assistant-huey.service %{buildroot}%{_unitdir}/
cp %{_sourcedir}/systemd/ciso-assistant-frontend.service %{buildroot}%{_unitdir}/

# Create symlink for db directory
ln -s /var/lib/ciso-assistant/db %{buildroot}/opt/ciso-assistant/backend/db
ln -s /var/lib/ciso-assistant/media %{buildroot}/opt/ciso-assistant/backend/media

# Create convenience wrapper scripts
cat > %{buildroot}%{_bindir}/ciso-assistant-manage <<'EOF'
#!/bin/bash
cd /opt/ciso-assistant/backend
exec /opt/ciso-assistant/venv/bin/python manage.py "$@"
EOF
chmod 755 %{buildroot}%{_bindir}/ciso-assistant-manage

%pre
# Create system user and group
if ! getent group ciso-assistant >/dev/null; then
    groupadd -r ciso-assistant
fi
if ! getent passwd ciso-assistant >/dev/null; then
    useradd -r -g ciso-assistant -d /opt/ciso-assistant -s /sbin/nologin \
        -c "CISO Assistant service account" ciso-assistant
fi

%post
# Generate Django secret key if not already set
if grep -q "__GENERATE_ON_INSTALL__" /etc/ciso-assistant/backend.env; then
    SECRET_KEY=$(/opt/ciso-assistant/venv/bin/python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    sed -i "s/__GENERATE_ON_INSTALL__/${SECRET_KEY}/" /etc/ciso-assistant/backend.env
fi

# Set proper ownership
chown -R ciso-assistant:ciso-assistant /opt/ciso-assistant
chown -R ciso-assistant:ciso-assistant /var/lib/ciso-assistant
chown -R ciso-assistant:ciso-assistant /etc/ciso-assistant
chmod 640 /etc/ciso-assistant/*.env

# Run Django migrations and collect static files
cd /opt/ciso-assistant/backend
sudo -u ciso-assistant /opt/ciso-assistant/venv/bin/python manage.py migrate --noinput 2>&1 | tee -a /opt/ciso-assistant/logs/install.log
sudo -u ciso-assistant /opt/ciso-assistant/venv/bin/python manage.py collectstatic --noinput 2>&1 | tee -a /opt/ciso-assistant/logs/install.log

# Reload systemd
systemctl daemon-reload

# Enable services (don't start automatically - let admin configure first)
systemctl enable ciso-assistant-backend.service
systemctl enable ciso-assistant-huey.service
systemctl enable ciso-assistant-frontend.service

echo ""
echo "============================================"
echo " CISO Assistant installed successfully!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Review configuration in /etc/ciso-assistant/"
echo "  2. Create superuser: ciso-assistant-manage createsuperuser"
echo "  3. Start services: systemctl start ciso-assistant-backend ciso-assistant-huey ciso-assistant-frontend"
echo "  4. Access application at http://localhost:3000"
echo ""
echo "View logs: journalctl -u ciso-assistant-backend -f"
echo ""

%preun
# Stop services before uninstall
if [ $1 -eq 0 ]; then
    systemctl stop ciso-assistant-frontend.service
    systemctl stop ciso-assistant-huey.service
    systemctl stop ciso-assistant-backend.service
    systemctl disable ciso-assistant-frontend.service
    systemctl disable ciso-assistant-huey.service
    systemctl disable ciso-assistant-backend.service
fi

%postun
# Clean up after uninstall
if [ $1 -eq 0 ]; then
    systemctl daemon-reload
    # Note: User, group, and data in /var/lib are preserved
    echo "Data preserved in /var/lib/ciso-assistant/"
    echo "Configuration preserved in /etc/ciso-assistant/"
fi

%files
%defattr(-,root,root,-)
/opt/ciso-assistant/
%{_unitdir}/ciso-assistant-backend.service
%{_unitdir}/ciso-assistant-huey.service
%{_unitdir}/ciso-assistant-frontend.service
%{_bindir}/ciso-assistant-manage
%dir /var/lib/ciso-assistant
%dir /var/lib/ciso-assistant/db
%dir /var/lib/ciso-assistant/media

%config(noreplace) /etc/ciso-assistant/backend.env
%config(noreplace) /etc/ciso-assistant/frontend.env

%changelog
* 2025-11-27 CISO Assistant Team <hello@intuitem.com>
- Initial RPM package for air-gapped deployment
- Includes bundled Python 3.12, Node.js 22, and all dependencies
- SQLite database for simplified deployment
- Systemd service management for backend, huey, and frontend
