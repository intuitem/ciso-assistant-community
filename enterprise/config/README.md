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
- **Database**: SQLite (simple, ideal to get started) or PostgreSQL (recommended for production)
- **Reverse proxy**: Caddy (default, simpler) or Traefik
- **Email**: SMTP configuration for sending notifications (optional)
- **License**: number of seats and expiration date
- **Debug**: enable or disable debug mode

Once complete, a `docker-compose.yml` file is automatically generated.

### 4. Start the application

#### First time only

The initialization script handles everything (pull, start, and admin account creation):

```bash
./docker-compose.sh
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
docker compose exec -it backend poetry run python manage.py createsuperuser
```

### 5. Connect

Open your browser at:

```
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

```bash
cd enterprise/config
docker compose pull
docker compose up -d
```

Database migrations are applied automatically on restart.

> Never delete the `db/` folder — it contains your database and uploaded files.

---

## Troubleshooting

| Symptom                 | What to do                                                                          |
| ----------------------- | ----------------------------------------------------------------------------------- |
| Application won't start | Run `docker compose logs backend` to check errors                                 |
| License error           | Check `LICENSE_SEATS` and `LICENSE_EXPIRATION` values in `docker-compose.yml` |
