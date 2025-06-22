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

3. Start a development server (make sure that the backend is running)

```bash
make dev
```

## Building

To create a production version of your app:

```bash
make
```
