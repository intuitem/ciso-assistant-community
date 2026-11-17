---
description: >-
  Every endpoint of the CISO Assistant REST API, generated from the OpenAPI
  specification of the latest release, plus the conventions shared by all of
  them.
---

# API reference

The pages below are generated from the API's OpenAPI specification and refreshed on every release, so they always match the latest version. There is one page per resource, and modules such as EBIOS RM or Privacy group their resources under a parent page. Use the download link on any page to get the full specification for your own tooling (Postman, client generators, and so on).

To authenticate, send a [personal access token](../integrations/pat.md) as `Authorization: Token <PAT>`. The [overview](../integrations/api.md) covers authentication, allowed IPs and a first request.

## Conventions

These rules apply to every resource, so they are described here once rather than on each page.

### Pagination

List endpoints take `limit` and `offset` and return a `count`, `next`, `previous` and `results` envelope. Follow `next` until it is `null` to read a whole collection. Page sizes and limits are described in [API pagination](../configuration/settings/api-pagination.md).

### Filtering, search and ordering

List endpoints accept their filters as query parameters. Date and number filters take a suffix that sets the comparison:

| Suffix     | Meaning                  | Example                              |
| ---------- | ------------------------ | ------------------------------------ |
| `__gt`     | strictly after / greater | `created_at__gt=2026-01-01T00:00:00Z` |
| `__gte`    | on or after              | `created_at__date__gte=2026-01-01`   |
| `__lt`     | strictly before / lower  | `updated_at__date__lt=2026-07-01`    |
| `__lte`    | on or before             | `updated_at__date__lte=2026-06-30`   |
| `__isnull` | value is missing or not  | `created_at__isnull=false`           |

Add `__date` to compare a timestamp by its day only. Most list endpoints also accept `search` for free-text search and `ordering` to sort, with a leading `-` for descending order (`ordering=-created_at`).

### Sparse fields

`?fields=a,b,c` trims a `GET` response to the listed fields, which keeps large lists light. An unknown field name is rejected with HTTP 400.

### Trailing slash

Always include the trailing slash: `/api/assets/`, not `/api/assets`.
