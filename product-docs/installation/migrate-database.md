---
description: >-
  You think it is time to change or try a new database on CISO Assistant? You
  were using SQLite and now want to switch to PostgreSQL, or the other way
  around? This guide is for you.
---

# Migrate between different databases

## Primordial step: create backups

{% hint style="warning" %}
Do not forget that this kind of operation can be tricky and may impact your data if something goes wrong.
{% endhint %}

To stay safe, we strongly recommend creating a backup of the volume, disk, or `db/` folder used to host your CISO Assistant instance.

We also recommend testing your backup procedure by deploying another CISO Assistant instance and restoring the backup into it. This will help verify that your backups work correctly before you start switching database engines.

## Switch from SQLite to PostgreSQL

Here is a complete guide of all the steps you should perform (after backing up your volume).

{% hint style="warning" %}
The new PostgreSQL-backed instance must run the **exact same CISO Assistant version** as the source SQLite instance. The restore will refuse a backup produced by a different version. Migrate first, then upgrade afterwards if needed.
{% endhint %}

### 1. Export your data

To facilitate the backup and restore workflow, we designed a backup-restore page with a button to back up the database.

Go in **Extra > Backup & restore**, then click on **Export database**. You will get a `.bak` file.

{% hint style="info" %}
Evidence files and other uploaded files are **not** included in this export — they live on disk under `db/attachments/` and are handled separately in step 7. If you'd rather get both the database and the attachments in a single bundle, skip this step and use the `clica` CLI instead — see step 7, Option B.
{% endhint %}

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


If PostgreSQL is running on your **host** (not in a container), set `DB_HOST=host.docker.internal` and add the following to your backend service:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

{% hint style="info" %}
The exact host settings depend on your setup — OS, Docker version, whether you run rootless Docker, or whether you bridge the backend container to the host network. Adjust `DB_HOST` and `extra_hosts` accordingly.
{% endhint %}

### 5. Restart, migrate and create a superuser

Bring the stack back up — if you are using Docker, migrations run automatically at startup:

```bash
docker compose up -d
```

Since the PostgreSQL database is brand new and empty, you also need to create a temporary superuser:

```bash
docker exec -it backend uv run python manage.py createsuperuser
```


{% hint style="info" %}
This is a temporary user. The backup restore will delete it while giving you back your original users.
{% endhint %}

### 6. Restore your data

Connect with your new temporary superuser, go to the **Backup & restore** section, and click the restore button. Select the `.bak` file you downloaded in step 1.

Your database will be fully restored. Reconnect with one of your original users.

### 7. Make sure evidence files are still reachable

The `.bak` only contains database rows. The actual evidence files (PDFs, images, …) live on the filesystem under `db/attachments/`, independent of which database engine you use. Database rows reference them by path, so if the files aren't where the rows expect them, evidence records will appear to exist but their attachments will be broken.

You have two ways to keep them:

**Option A — Same host, same volume (typical case).** If you're switching the database engine in place on the same machine and you kept the `db/` volume mounted on the new stack, you don't need to do anything: `db/attachments/` is already there and the restored records will resolve to the existing files.

**Option B — Cross-host migration, or you want one atomic snapshot.** Use the `clica` CLI shipped under [`cli/`](https://github.com/intuitem/ciso-assistant-community/tree/main/cli) instead of the UI export. It packages the database **and** every attachment in a single backup, then restores both in one atomic call:

```bash
# On the source instance — produces backup.json.gz + attachments/ + manifest
uv run clica.py backup-full --dest-dir ./db_backup

# On the new (PostgreSQL-backed) instance, after step 5
uv run clica.py restore-full --src-dir ./db_backup
```

Requires a Personal Access Token with the backup permission set in `.clica.env`. The CLI verifies SHA-256 hashes and is resumable. See `cli/README.md` for setup details.

## Switch from PostgreSQL to SQLite

The logic is the same in reverse:

1. Export the database from the **Extra > Backup & restore** page on your PostgreSQL-backed instance (or run `clica backup-full` if you want attachments included).
2. Stop the stack (`docker compose down`).
3. Remove the PostgreSQL environment variables (`POSTGRES_NAME`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_HOST`, `DB_PORT`) and the `db` service from your `docker-compose.yml`. With `POSTGRES_NAME` unset, CISO Assistant falls back to SQLite at `db/ciso-assistant.sqlite3`.
4. Bring the stack back up, create a temporary superuser, and restore the `.bak` file (or run `clica restore-full`).
5. Keep `db/attachments/` in place — the same caveat from step 7 above applies.

The same version-match rule applies: the SQLite-backed instance must run the exact same CISO Assistant version as the PostgreSQL-backed source.
