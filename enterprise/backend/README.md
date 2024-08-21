# Quick start (development)

1. Install the `enterprise_core` package

```bash
cd enterprise/backend
poetry install
```

2. Start the development server with the enterprise settings file

```bash
python manage.py runserver --settings=enterprise_core.settings
```

# Running a white label instance

This can be done by running the development server with the `FF_WHITE_LABEL` environment variable set to `true`.

```bash
export FF_WHITE_LABEL=true
python manage.py runserver --settings=enterprise_core.settings
```
