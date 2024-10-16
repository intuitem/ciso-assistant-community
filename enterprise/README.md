## Testing locally 🚀

To run CISO Assistant Enterprise locally in a straightforward way, you can use Docker compose.

1. Make sure you are located in the enterprise directory of the repository

2. Launch docker-compose script with enterprise docker-compose.yml file:

```sh
./docker-compose-build.sh -f enterprise/docker-compose-build.yml
```

When asked for, enter your email and password for your superuser.

You can then reach CISO Assistant using your web browser at [https://localhost:8443/](https://localhost:8443/)

## Setting up CISO Assistant Enterprise for development

> [!NOTE]
> This section assumes that you have already set up the community frontend and backend, and use poetry for managing the backend dependencies.

### Running the backend

1. Go to community backend directory.

```sh
cd ../backend
```

2. Open poetry shell.

```sh
poetry shell
```

3. Install enterprise backend module.

```sh
cd ../enterprise/backend
poetry install
```

4. Set the `SQLITE_FILE` environment variable if you use SQLite.

```sh
export SQLITE_FILE=db/ciso-assistant-enterprise.sqlite3
```

5. Apply migrations.

```sh
poetry run ./manage.sh migrate
```

6. Create a Django superuser, that will be CISO Assistant administrator.

```sh
poetry run ./manage.sh createsuperuser
```

7. Run the development server.

```sh
poetry run ./manage.sh runserver
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
