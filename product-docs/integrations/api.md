# API reference

CISO Assistant exposes a REST API that mirrors the platform's object model. The same API powers the SvelteKit frontend, the CLI, the MCP server, and every external integration — there is no separate "public" surface to maintain. Anything you can do in the UI, you can do over HTTP.

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

## What this section will cover

- **Resource model** — viewsets, the universal `folder` scoping field, IAM filtering rules, pagination and filtering conventions.
- **Common patterns** — batch actions, the `for_object` action style, mass-import via `data_wizard`, exporting and importing libraries.
- **Webhooks and async** — Huey-backed background tasks and how their results surface in the API.
- **Integrations** — MCP server, CLI, Excel import/export, Power BI connector, library YAML format.

## Related

- [Philosophy → Open by default, extensible by design](../introduction/philosophy.md)
