---
description: >-
  How the CISO Assistant API paginates list endpoints, and the PAGINATE_BY /
  PAGINATE_MAX environment variables that control the default page size and
  the maximum a client can request.
---

# API pagination

## What it does

Every list endpoint of the API returns a paginated envelope:

```json
{
  "count": 1234,
  "next": "/api/assets/?limit=100&offset=100",
  "previous": null,
  "results": ["..."]
}
```

A single request never returns more than the configured maximum page size. To
retrieve a complete collection, follow the `next` link (or increase `offset`)
until `next` is `null` — `count` always holds the true total, so a response
with fewer rows than `count` is a page, not the whole dataset.

## Environment variables

| Variable       | Default                  | Meaning                                                                          |
| -------------- | ------------------------ | -------------------------------------------------------------------------------- |
| `PAGINATE_BY`  | `100`                    | Page size applied when a request passes no `limit` parameter.                    |
| `PAGINATE_MAX` | `max(5000, PAGINATE_BY)` | Hard ceiling for the `limit` parameter. Larger values are clamped, never served. |

The default page size can never exceed the ceiling: if `PAGINATE_BY` is set
above `PAGINATE_MAX`, the effective page size is `PAGINATE_MAX`. Because the
ceiling follows `PAGINATE_BY` upward, raising only `PAGINATE_BY` raises both.

{% hint style="info" %}
The ceiling is deliberately generous today so that existing integrations
keep working. It is expected to come down to 200 in a future release — build
new clients to follow `next` rather than to request a large `limit`.
{% endhint %}

## Client rules

* `limit` must be a strictly positive integer and `offset` a non-negative
  integer — anything else (including `limit=0`, which never meant "no limit")
  is rejected with **HTTP 400**.
* A `limit` above `PAGINATE_MAX` is silently clamped: the response then holds
  fewer rows than requested and a non-null `next` link.
* Never infer completeness from a single response — check `next` and `count`.
* Sort order is deterministic: every ordering carries a unique tiebreaker, so
  paging through a collection neither skips nor duplicates rows. Rows created
  or deleted **while** you page can still shift across page boundaries.

{% hint style="warning" %}
Releases prior to this change defaulted to 5,000-row pages, which let scripts
fetch most collections in a single request. A client that sends no `limit` now
receives 100 rows per page. If an integration relies on the old behaviour,
teach it to follow `next` links (recommended), or have it request an explicit
`limit` — up to `PAGINATE_MAX`, which still allows 5,000. As a transition
workaround, `PAGINATE_BY=5000` restores the old **default page size** —
responses remain paginated envelopes, invalid `limit`/`offset` values are
still rejected, and collections larger than the page size still require
following `next`.
{% endhint %}
