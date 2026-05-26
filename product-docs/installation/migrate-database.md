---
description: >-
  You think it is time to change or try a new database on CISO Assistant? You
  were using SQLite and now want to switch to PostgreSQL, or the other way
  around? This guide is for you.
---

# Migrate between different databases

## Primordial step: create backups

> Do not forget that this kind of operation can be tricky and may impact your data if something goes wrong.

To stay safe, we strongly recommend creating a backup of the volume, disk, or `db/` folder used to host your CISO Assistant instance.

We also recommend testing your backup procedure by deploying another CISO Assistant instance and restoring the backup into it. This will help verify that your backups work correctly before you start switching database engines.

## Switch from SQLite to PostgreSQL

Here is a complete guide of all the steps you should perform (after backing up your volume).

### 1. Export your data

To facilitate the backup and restore workflow, we designed a backup-restore page with a button to back up all your data, excluding images and evidences. Don't worry, you won't lose them.

Go in EXTRA > Backup & restore

Click on **Export database** and you are good to go.

### 2. Stop the instance of CISO Assistant

```bash
docker compose down
```

### 3. Set up PostgreSQL

You can install whichever PostgreSQL setup you prefer, as you only need the environment variables afterwards to connect it to CISO Assistant. Here are the two main ways:

#### On your host using a service

Depending on your OS, install PostgreSQL — here on Ubuntu:

```bash
sudo apt install postgresql
```

Configure your PostgreSQL instance with at minimum:

```
POSTGRES_DB=ciso-assistant
POSTGRES_USER=ciso-assistantuser
POSTGRES_PASSWORD=<choose a password>
```

Also check the port on which PostgreSQL is running (normally `5432`).

#### In a Docker container

In your `docker-compose.yml`, add a service like this:

```yaml
db:
  container_name: db
  image: postgres:16
  restart: always
  environment:
    - POSTGRES_DB=ciso-assistant
    - POSTGRES_USER=ciso-assistantuser
    - POSTGRES_PASSWORD=<your pg password>
  volumes:
    - ./pgdata:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ciso-assistantuser -d ciso-assistant"]
    interval: 10s
    timeout: 5s
    retries: 10
    start_period: 50s
```

### 4. Connect CISO Assistant to PostgreSQL

Define these environment variables in your `docker-compose.yml` (or via `export` if running without containers):

```
POSTGRES_NAME=ciso-assistant
POSTGRES_USER=ciso-assistantuser
POSTGRES_PASSWORD=<your pg password>
DB_HOST=db
DB_PORT=5432
```


If PostgreSQL is running on your **host** (not in a container), set `DB_HOST=host-gateway` and add the following to your backend service:

```yaml
extra_hosts:
  - "host-gateway:host-gateway"
```

### 5. Restart, migrate and create a superuser

Bring the stack back up — if you are using Docker, migrations run automatically at startup:

```bash
docker compose up -d
```

Since the PostgreSQL database is brand new and empty, you also need to create a temporary superuser:

```bash
docker exec -it backend poetry run python manage.py createsuperuser
```


> This is a temporary user. The backup restore will delete it while giving you back your original users.

### 6. Restore your data

Connect with your new temporary superuser, go to the **Backup & Restore** section, and click the restore button. Select the `.bak` file you downloaded in step 1.

Your data will be fully restored. Reconnect with your original user — all your sessions and attachments will be there.
