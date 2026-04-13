> [!WARNING]
> Both installation assume you're located in the root folder (`ciso-assistant-community/`)

## Testing locally 🚀

New: use the config builder on the `config` folder.

To run CISO Assistant Enterprise locally in a straightforward way, you can use Docker compose.

1. Launch docker-compose script with enterprise docker-compose.yml file:

```sh
./docker-compose-build.sh -f enterprise/docker-compose-build.yml
```

When asked for, enter your email and password for your superuser.

You can then reach CISO Assistant using your web browser at [https://localhost:8443/](https://localhost:8443/)

## Setting up CISO Assistant Enterprise for development

> [!NOTE]
> This section assumes that you have already set up the community frontend and backend, and use uv for managing the backend dependencies.

### Running the backend

1. Go to enterprise backend directory.

```sh
cd enterprise/backend
```

2. Install dependencies.

```sh
uv sync
```

3. Set the `SQLITE_FILE` environment variable if you use SQLite.

```sh
export SQLITE_FILE=db/ciso-assistant-enterprise.sqlite3
```

4. Apply migrations.

```sh
uv run ./manage.sh migrate
```

5. Create a Django superuser, that will be CISO Assistant administrator.

```sh
uv run ./manage.sh createsuperuser
```

6. Run the development server.

```sh
uv run ./manage.sh runserver
```

### Running the frontend

1. cd into the enteprise frontend directory.

```bash
cd enterprise/frontend
```

3. Start a development server (make sure that the django app is running).

```bash
make dev
```

4. Reach the frontend on <http://localhost:5173>
