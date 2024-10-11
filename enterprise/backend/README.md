# Quick start (development)

1. Make sure you opened `poetry shell` in community backend and are in the `enterprise/backend` directory

```bash
cd backend
poetry shell
cd ../enterprise/backend
```

2. Install the `enterprise_core` package

```bash
poetry install
```

3. Start the development server with the enterprise settings file

```bash
poetry run manage.sh runserver
```
