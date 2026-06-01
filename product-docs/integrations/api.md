# API reference

CISO Assistant exposes a REST API that mirrors the platform's object model. The same API powers the web frontend, the CLI, the MCP server, and every external integration. Anything you can do in the UI, you can do over HTTP.

## Authentication

The API uses token-based authentication. To call any endpoint:

1. **Create a Personal Access Token (PAT)** from your user profile in the application.
2. **Add the token to the `Authorization` header** of every request:

   ```
   Authorization: Token <your_token>
   ```

Example with curl:

```sh
curl --request GET \
  --url https://your-instance/api/assets/ \
  --header 'Authorization: Token a6a120f...'
```

Notes:

- Always include the trailing slash on endpoints (`/api/assets/`, not `/api/assets`).
- Your endpoint URL is your instance URL with `/api/` appended (assuming default proxy settings).
- Pro SaaS users need to open a support request to expose the API on their instance — it is disabled by default.

## Browsing the schema

Two ways to read the API surface:

- **Live online docs** — [ca-api-doc.pages.dev](https://ca-api-doc.pages.dev).
- **On your instance, in debug mode** — set `DJANGO_DEBUG=True`, start the backend, then browse:
  - Swagger UI: `http://127.0.0.1:8000/api/schema/swagger/`
  - ReDoc: `http://127.0.0.1:8000/api/schema/redoc/`

## Related

- [Philosophy → Open by default, extensible by design](../introduction/philosophy.md)
