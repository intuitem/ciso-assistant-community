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
  "next": "/api/assets/?limit=5000&offset=5000",
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
| `PAGINATE_BY`  | `5000`                   | Page size applied when a request passes no `limit` parameter.                    |
| `PAGINATE_MAX` | `max(5000, PAGINATE_BY)` | Hard ceiling for the `limit` parameter. Larger values are clamped, never served. |

The default page size can never exceed the ceiling: if `PAGINATE_BY` is set
above `PAGINATE_MAX`, the effective page size is `PAGINATE_MAX`. Because the
ceiling follows `PAGINATE_BY` upward, raising only `PAGINATE_BY` raises both.

{% hint style="info" %}
The ceiling is deliberately generous today so that existing integrations
keep working. It is expected to come down to 200 in a future release — build
new clients to follow `next` rather than to request a large `limit`.
{% endhint %}

{% hint style="warning" %}
**Power BI connector 1.0.2 and older truncate their imports** on an instance
where `PAGINATE_MAX` is below 5000: they page by the `limit` they asked for
rather than the number of rows served, so each table stops after one page —
with no error. Connector 1.1.0 and later read the page size back from the
response and are correct at any ceiling. Upgrade every desktop and gateway
running the connector before lowering `PAGINATE_MAX`.
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
The default page size is unchanged, but `limit` and `offset` validation is
stricter: values that are not positive integers are rejected with **HTTP 400**
instead of falling back to the default, so a client sending `limit=0` now gets
an error where it previously got a full page.
{% endhint %}

## Selecting fields

A `GET` on a list or detail endpoint accepts `fields`, a comma-separated list
of the columns to return:

```
GET /api/applied-controls/?fields=id,name,status
GET /api/risk-scenarios/?fields=id,applied_controls
```

This is worth using when a bulk reader needs one or two columns out of a wide
row — building a link table between two objects, for instance, or exporting a
single attribute for every record. Responses get smaller and the server does
less work per row.

* The parameter can only **narrow** a response, never widen one. A name the
  endpoint does not expose — a model column it does not publish, or a field
  belonging to a disabled feature — is rejected with **HTTP 400**.
* Fields hidden from your role are still hidden: naming one is accepted, and
  the response simply does not contain it, exactly as without the parameter.
* `id` is always included, even when it is not requested.
* Names are the top-level keys of the response, not paths: request `folder`,
  not `folder.name`. The whole nested object is returned.
* Everything else is unchanged — permissions, pagination, filters and ordering
  behave exactly as they do without the parameter.

{% hint style="info" %}
The Power BI connector uses this from version 1.1.0 for its bridge tables. An
older instance that does not know the parameter simply ignores it and returns
full rows, so the connector keeps working either way.
{% endhint %}
