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
- API access is IP-restricted: the calling machine must be on the [Allowed IPs whitelist](../configuration/settings/infra-config-allowed-ip.md) (**Settings → Infrastructure**). On SaaS the allowlist is self-service and API access is closed until you add your caller IPs; on-premises, enable the allowlist with `ENABLE_INFRA_CONFIG_MANAGEMENT=True` or handle IP filtering in your own infrastructure.

## Browsing the schema

Two ways to read the API surface:

- **Live online docs** — [ca-api-doc.pages.dev](https://ca-api-doc.pages.dev).
- **On your instance, in debug mode** — set `DJANGO_DEBUG=True`, start the backend, then browse:
  - Swagger UI: `http://127.0.0.1:8000/api/schema/swagger/`
  - ReDoc: `http://127.0.0.1:8000/api/schema/redoc/`

## Related

- [Allowed IP whitelist](../configuration/settings/infra-config-allowed-ip.md) — open API access to your callers
- [Philosophy → Open by default, extensible by design](../introduction/philosophy.md)
