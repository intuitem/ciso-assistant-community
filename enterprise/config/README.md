# Installing CISO Assistant Enterprise with Docker

## Prerequisites

- Docker and Docker Compose installed
- Python 3.10+
- Access to the Enterprise Docker images (provided by Intuitem)

## Installation in 5 steps

### 1. Clone the repository

```bash
git clone https://github.com/intuitem/ciso-assistant-community.git
cd ciso-assistant-community
```

### 2. Install the configuration dependencies

```bash
cd enterprise/config
pip install -r requirements.txt
```

### 3. Generate the Docker configuration

```bash
python make_config.py
```

The script guides you step by step with simple questions:

- **Deployment**: local or on a remote server?
- **HTTPS certificate**: automatic Let's Encrypt, your own certificate, or self-signed (default)
- **Address and port**: your domain name (e.g. `grc.company.com`) and access port (default `8443`)
- **Database**: SQLite (simple, no database to administer) or PostgreSQL (for larger deployments)
- **Reverse proxy**: Caddy (default, simpler) or Traefik
- **Email**: SMTP configuration for sending notifications (optional)
- **License**: number of seats and expiration date
- **Memcached**: optional shared cache for the backend workers, so login rate limits are counted across all workers (disabled by default)
- **Debug**: enable or disable debug mode

Once complete, a `docker-compose.yml` file is automatically generated.

#### Which options to choose?

| Question | Trial / local test | Production |
| --- | --- | --- |
| Deployment mode | `local` | `VM/Remote` |
| Internet-facing host (ACME) | No | Yes if the server is publicly reachable under its domain, otherwise No |
| Custom certificates | No (self-signed, the browser shows a warning) | Yes if your organization provides a certificate for the domain |
| FQDN/hostname | `localhost` | The domain users will type, e.g. `grc.company.com` |
| Port | `8443` | `8443`, or `443` if nothing else listens on it |
| Database | `sqlite` | `sqlite` for a small team, `postgresql` for a larger one |
| Proxy | `caddy` | `caddy`, or `traefik` if your team already runs it |
| Email notifications | No | Yes, with your company SMTP relay |
| Memcached | No | Yes |
| Debug mode | No | No |

Some tips:

- **Use a domain name, not an IP address.** With an IP, browsers don't send the server name during the TLS handshake and the proxy can't serve the certificate. If you have no DNS entry yet, add one to each client's `/etc/hosts` (or `C:\Windows\System32\drivers\etc\hosts`).
- **Let's Encrypt (ACME)** only works if the server is publicly reachable under that domain. With Caddy, use port `443` so the challenge can succeed. For an internal server, answer No and provide your company certificate, or keep the self-signed one.
- **Custom certificate paths** are relative to `enterprise/config`. The certificate file should contain the full chain (server certificate followed by intermediates).
- **SQLite** is a good choice in production for a small team, or if you are not comfortable administering PostgreSQL: the whole database is a file in `db/`, backed up by copying that folder with the application stopped. Choose **PostgreSQL** for many concurrent users or if your team already operates it, and change its default password.
- **Email** is needed for password reset links, invitations and notifications. The default `host.docker.internal:1025` only targets a local test mailer: replace it with your SMTP server (usually port `587` with TLS).
- **License** values must match the license provided by intuitem. They can be edited later in `docker-compose.yml` (`LICENSE_SEATS`, `LICENSE_EXPIRATION`).
- **Memcached** adds one small container, isolated from the network. Enable it in production so login rate limiting is consistent across workers.
- **Debug mode** exposes internal details in error pages. Keep it disabled outside development.

You can run `python make_config.py` again at any time to regenerate `docker-compose.yml`. Manual edits to that file are overwritten.

### 4. Start the application

#### First time only

The initialization script handles everything (pull, start, and admin account creation):

```bash
./docker-compose.sh     # Linux/MacOS
./docker-compose.ps1    # Windows
```

> This script only works on a fresh install (no existing `db/` folder). For all subsequent operations, use the manual commands below.

#### Manual commands (start, stop, restart)

```bash
docker compose pull          # download the latest images
docker compose up -d         # start all services
docker compose down          # stop all services
docker compose up -d         # restart
```

To create an admin account manually:

```bash
docker compose exec -it backend uv run python manage.py createsuperuser
```

### 5. Connect

Open your browser at:

```text
https://your-domain:8443
```

Replace `your-domain` with the domain name you entered in step 3.

---

## Stopping the application

```bash
cd enterprise/config
docker compose down
```

This stops and removes all containers. Your data in `db/` is preserved.

---

## Updating

### Recommended: pin a specific version

By default, the generated `docker-compose.yml` uses the `latest` tag for backend and frontend images. For production, we recommend pinning a specific version to control when upgrades happen.

In your `docker-compose.yml`, replace:

```yaml
image: ghcr.io/intuitem/ciso-assistant-enterprise-backend:latest
image: ghcr.io/intuitem/ciso-assistant-enterprise-frontend:latest
```

Available versions can be found on the [releases page](https://github.com/intuitem/ciso-assistant-community/releases).

Replace with a specific version tag (e.g. `v1.0.0`):

```yaml
image: ghcr.io/intuitem/ciso-assistant-enterprise-backend:v1.0.0
image: ghcr.io/intuitem/ciso-assistant-enterprise-frontend:v1.0.0
```

Then to upgrade, update the tag to the desired version and run:

```bash
cd enterprise/config
docker compose up -d
```

### Alternative: use latest

If you prefer to always track the latest release:

```bash
cd enterprise/config
docker compose pull
docker compose up -d
```

> **Note**: `pull_policy: always` is set on application services, so `docker compose up -d` will also pull newer images if available. Running `docker compose pull` first ensures all images are updated before restarting.

Database migrations are applied automatically on restart.

> Never delete the `db/` folder — it contains your database and uploaded files.

---

## Troubleshooting

| Symptom                 | What to do                                                                    |
| ----------------------- | ----------------------------------------------------------------------------- |
| Application won't start | Run `docker compose logs backend` to check errors                             |
| License error           | Check `LICENSE_SEATS` and `LICENSE_EXPIRATION` values in `docker-compose.yml` |
| Backend can't reach memcached | Check `docker compose logs memcached`; the `memcached_socket` volume must be shared by `backend` and `huey` |
