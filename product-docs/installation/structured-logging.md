---
description: >-
  CISO Assistant can emit its operational logs as line-delimited JSON so a SIEM
  (Microsoft Sentinel, Azure Data Explorer, Splunk, Elastic) can ingest them
  without custom parsing. This page explains how to enable it and what the
  records look like.
---

# Structured logging

## Overview

The three runtime processes each write their operational logs to standard output, where your container runtime or log shipper collects them:

* **Backend** (Django API)
* **Worker** (the Huey background task process)
* **Frontend** (the SvelteKit server-side process)

By default the output is a human-readable, colourised format meant for reading in a terminal. That format is convenient locally but awkward to parse in a log pipeline. Setting a single environment variable switches every stream to **one JSON object per line** (newline-delimited JSON), which SIEMs parse natively.

{% hint style="info" %}
This page is about the **operational log streams** (requests, errors, background-task activity, authentication events). It is distinct from the in-app [Audit log](../features/audit-log.md), which records who changed which object and is read inside the application.
{% endhint %}

## Enabling JSON logs

Set the following on the **backend**, **worker**, and **frontend** containers:

```bash
LOG_FORMAT=json   # default: plain
```

The backend and the Huey worker share the same logging configuration, so this one variable covers both. Setting it on the frontend container routes the SvelteKit server process — authentication events, request errors — through the same JSON shape.

The log level defaults to `INFO`, which captures request-level events. Adjust it if you need more or less detail:

```bash
LOG_LEVEL=INFO    # default: INFO. Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

{% hint style="warning" %}
Set `LOG_FORMAT=json` on **all three** containers. If only some are switched, your pipeline receives a mix of JSON and plain-text lines and parsing breaks for the plain ones.
{% endhint %}

## What the records look like

A backend request log line (formatted here for readability — on the wire it is a single line):

```json
{
  "request": "GET /api/folders/",
  "code": 200,
  "request_id": "0d6f1c4e-2a8b-4e1f-9c3a-7b2e5f0a1d44",
  "user_id": 1,
  "ip": "10.0.2.15",
  "ciso_assistant_url": "https://ciso.example.com",
  "event": "request_finished",
  "timestamp": "2026-06-12T09:21:33.123456Z",
  "level": "info",
  "logger": "django_structlog.middlewares.request"
}
```

A frontend authentication event:

```json
{
  "timestamp": "2026-06-12T09:21:34.001Z",
  "level": "warning",
  "logger": "frontend",
  "event": "Login failed",
  "status": 400
}
```

### Common fields

| Field | Description |
| --- | --- |
| `timestamp` | ISO-8601 UTC timestamp |
| `level` | `debug`, `info`, `warning`, `error`, `critical` |
| `logger` | Source logger (`frontend` for the SvelteKit process; a Python module path on the backend) |
| `event` | The log message |
| `request_id` | Correlation id shared by all backend log lines from one request |
| `user_id` | Authenticated user id, when the request is authenticated |
| `ip` | Client IP address |

Sensitive OAuth2 query parameters (`code`, `token`, `id_token`, `access_token`) are redacted from logged request URLs.

## Optional: also write the backend log to a file

In addition to standard output, the backend can mirror its logs to a file (always in JSON, regardless of `LOG_FORMAT`):

```bash
LOG_OUTFILE=ciso-assistant.log
```

This is useful when a log shipper tails a file rather than the container's stdout.

## Shipping to a SIEM

Once `LOG_FORMAT=json` is set, point your collector at each container's stdout (or the file above). Because the lines are newline-delimited JSON, Microsoft Sentinel, Azure Data Explorer, Splunk and Elastic all parse them without a custom grok/regex parser — each JSON key becomes a queryable field. Use `request_id` to correlate all backend lines belonging to a single request, and `logger` to separate the frontend stream from the backend stream.
