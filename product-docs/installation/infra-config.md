---
description: >-
  CISO Assistant can let administrators manage infrastructure configuration
  settings — currently the list of IPs/CIDRs allowed to reach the backend — and
  expose them to the infrastructure layer through an /infra-config/ endpoint.
  This page explains how to enable it and how to consume it safely.
---

# Infrastructure configuration

## Overview

When enabled, administrators can manage infrastructure configuration settings
from **Settings → Infrastructure**. Today this is the list of IP addresses and
CIDR ranges allowed to reach the backend API; the endpoint is designed to grow
more settings over time.

These settings are exposed through an unauthenticated `/infra-config/` endpoint
so the infrastructure layer (reverse proxy, firewall, security group, …) can
consume them and configure access automatically — instead of opening a support
ticket every time a new IP needs to be allowed.

### Enabling the feature

Set the following environment variable on the backend container:

```bash
ENABLE_INFRA_CONFIG_MANAGEMENT=True
```

The feature is disabled by default (`ENABLE_INFRA_CONFIG_MANAGEMENT=False`). When
disabled, the settings tab is hidden and the `/infra-config/` endpoint is not
registered.

### Security — never expose `/infra-config/` publicly

{% hint style="danger" %}
The `/infra-config/` endpoint is **unauthenticated**, exactly like `/metrics`. If
you enable it, make sure it is never reachable from the public internet — either
by restricting access to trusted IP ranges, or by binding the endpoint to an
internal interface only.
{% endhint %}

### Consuming the endpoint

From a machine that has access to the backend (not from the public internet):

```bash
curl http://localhost:8000/infra-config/
```

The response is a JSON object:

```json
{
  "allowed_ips": ["203.0.113.4", "198.51.100.0/24"]
}
```

If the endpoint returns a 404, check that `ENABLE_INFRA_CONFIG_MANAGEMENT=True` is
set and that the backend has restarted.
