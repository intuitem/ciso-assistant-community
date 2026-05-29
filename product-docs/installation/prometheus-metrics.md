---
description: >-
  CISO Assistant exposes a /metrics endpoint in the Prometheus exposition format.
  This page explains how to enable it and how to access it safely from Prometheus
  without exposing it publicly.
---

# Prometheus metrics

### Overview

When enabled, the backend exposes a `/metrics` endpoint that returns instance-level gauges in the [Prometheus exposition format](https://prometheus.io/docs/instrumenting/exposition_formats/):

* User and editor counts
* Number of loaded libraries, domains, perimeters, assets, threats
* Number of compliance assessments, risk assessments, risk scenarios, risk acceptances
* Number of applied controls and evidences
* License expiration date, instance creation date, last login date
* Build information (version, commit, schema)

### Enabling the endpoint

Set the following environment variable on the backend container:

```bash
EXPOSE_METRICS=True
```

The endpoint is disabled by default (`EXPOSE_METRICS=False`).

### Security — never expose `/metrics` publicly

{% hint style="danger" %}
The `/metrics` endpoint is **unauthenticated**. It must never be reachable from the public internet. Always block it at the reverse proxy level and only allow access from your internal network or from Prometheus itself.
{% endhint %}

Here is for example the caddy service we use in docker-compose.yml but we authorize a local prometheus to go search in it while not authorizing exterior connection to check:

```yaml
  backend:
    ...
    environment:
      - EXPOSE_METRICS=True
    ...
    ports:
      - "127.0.0.1:8000:8000"

  caddy:
    container_name: caddy
    image: caddy:2.11.2
    environment:
      - CISO_ASSISTANT_URL=https://localhost:8443
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    ports:
      - 8443:8443
    volumes:
      - ./db/caddy:/data/caddy
    command: |
      sh -c 'echo $$CISO_ASSISTANT_URL "{
      reverse_proxy /api/* backend:8000
      reverse_proxy /* frontend:3000
      tls internal
      }" > Caddyfile && caddy run'
```

### Prometheus configuration (single VM)

If your prometheus runs in local you can for example check the /metrics endpoint with this config 

```yaml
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: ciso-assistant
    static_configs:
      - targets:
          - localhost:8000  
    metrics_path: /metrics/
```

If you have multiple instances on different machines, add them to `targets`:

```yaml
    static_configs:
      - targets:
          - 192.168.1.10:8000
          - 192.168.1.11:8000
```

Start Prometheus with:

```bash
prometheus --config.file=prometheus.yml
```

The Prometheus UI is available at `http://localhost:9090`. Search for `ciso_assistant_nb_users` to confirm that scraping is working.

### Verifying the endpoint

From a machine that has access to the backend (not from the public internet):

```bash
curl http://localhost:8000/metrics
```

You should see output similar to:

```
# HELP ciso_assistant_nb_users Number of users in the CISO Assistant instance
# TYPE ciso_assistant_nb_users gauge
ciso_assistant_nb_users 3.0
...
```

If the endpoint returns a 404, check that `EXPOSE_METRICS=true` is set and that the backend has restarted.
