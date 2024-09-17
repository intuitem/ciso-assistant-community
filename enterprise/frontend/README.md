# Quick start (development)

1. Clone the repository
2. Create a `.env` file with environment variables or export them.

```bash
echo "PUBLIC_BACKEND_API_URL=http://127.0.0.1:8000/api" > .env
```

OR

```bash
export PUBLIC_BACKEND_API_URL=http://127.0.0.1:8000/api
```

3. Move community and enterprise code to a single directory and install dependencies

```bash
make pre-build
```

4. Start a development server (ensure that the django app is running)

```bash
make dev
```

## Building

To create a production version of your app:

```bash
make
```

# Running a white label instance

This can be done by running the development server with the `FF_WHITE_LABEL` environment variable set to `true`.

```bash
export FF_WHITE_LABEL=true
make dev
```
