# API reference

> _Draft — placeholder._

CISO Assistant exposes a REST API that mirrors the platform's object model. The same API powers the SvelteKit frontend, the CLI, the MCP server, and every external integration — there is no separate "public" surface to maintain. Anything you can do in the UI, you can do over HTTP.

## What this section should cover

- **Authentication** — token-based auth via `/api/iam/login/`, personal access tokens, header conventions.
- **Resource model** — viewsets, the universal `folder` scoping field, IAM filtering rules, pagination and filtering conventions.
- **Common patterns** — batch actions, the `for_object` action style, mass-import via `data_wizard`, exporting and importing libraries.
- **Schemas** — pointers to the OpenAPI/Swagger surface and how to keep client code in sync.
- **Webhooks and async** — Huey-backed background tasks and how their results surface in the API.

## Getting started

> _Draft._ Quick-start: enable `DJANGO_DEBUG=True`, hit `/api/iam/login/`, copy the token, browse `/api/schema/swagger/`. Add a curl example.

## Resource conventions

> _Draft._ One short paragraph per cross-cutting convention (folder scoping, soft delete absence, `urn` for built-ins, `WriteSerializer` vs `ReadSerializer`).

## Integrations

> _Draft — eventually a sub-section._ MCP server, CLI, Excel import/export, Power BI connector, library YAML format.

## Related

- Swagger UI in dev: `http://127.0.0.1:8000/api/schema/swagger/`
- [Philosophy → Open by default, extensible by design](../philosophy.md)
