---
description: >-
  By default, CISO Assistant refuses to send requests to private, loopback and
  internal addresses. This page explains which features it applies to, how to
  allow a model server, mail relay, ticketing tool or collector on your own
  network, and what that changes for security.
---

# Reaching services on a private network

## Overview

Several features make the backend send requests to a URL that an administrator types in. To prevent server-side request forgery (SSRF), where someone uses those requests to reach internal services, the backend only connects to public addresses. Private ranges (such as `10.0.0.0/8`, `192.168.0.0/16`), loopback (`localhost`, `127.0.0.1`), link-local (including the cloud metadata address `169.254.169.254`) and other internal addresses are refused. The check runs when you save the URL. For webhook and audit log deliveries, integrations and workflows, it runs again on each connection, so a host name that later resolves to a private address is refused too.

On-premises, the service you want to reach often lives on your own network. To allow that, set this environment variable:

```bash
ALLOW_PRIVATE_NETWORK_REQUESTS=True
```

Accepted values are `True`, `1` and `yes`, in any case. The default is `False`. This variable was previously named `WEBHOOK_ALLOW_PRIVATE_IPS`; the old name is no longer recognized.

{% hint style="info" %}
**On SaaS**, environment variables are managed by intuitem and cannot be set from your instance, and this one stays off: a SaaS instance runs on intuitem's network, so it could not reach your private network anyway. Give the service a public HTTPS address instead, protected by authentication, and if your firewall only accepts known senders, open a ticket on the [customer support portal](https://intuitem.atlassian.net/servicedesk/customer/portal/4) for the addresses to allow.
{% endhint %}

## Features it applies to

| Feature | URL that is checked |
| --- | --- |
| [AI providers](../integrations/ai-providers.md) and [Paul](../integrations/paul.md) | Ollama URL, OpenAI-compatible API base URL |
| [Mailer](mailer.md) | Mail server host, OAuth token URL |
| [Webhooks](../integrations/webhooks.md) | Endpoint URL |
| [Audit log forwarding](../integrations/audit-log-forwarding.md) | HTTP sink URL, OAuth token URL |
| [Jira](../integrations/third-party/jira.md), [ServiceNow](../integrations/third-party/servicenow.md), [GLPI](../integrations/third-party/glpi.md) | Instance URL |
| [Workflows](../features/workflows/permissions-and-security.md) | URLs called by **HTTP request** and **Attach a file to an evidence** steps |
| [Service accounts](../integrations/service-accounts.md) (federated) | Identity provider discovery and key URLs |

Images embedded in generated PDF documents are always fetched from public addresses only. The variable does not change that.

## Symptoms

Without the variable, a private address gives one of these errors:

* `URL must point to a public address.` when saving an AI provider URL;
* `URL must point to a public host (no private, loopback, or internal addresses).` when saving an audit log sink;
* `... must resolve to a public address (set ALLOW_PRIVATE_NETWORK_REQUESTS=True to allow private networks)` when saving the mailer;
* `Jira server_url URL must be a public HTTPS endpoint` (or `ServiceNow instance_url`, `GLPI instance_url`) when an integration connects;
* `Blocked: ... URL points to a non-public address` in the logs of a webhook or audit log delivery;
* for the chat assistant, a reply starting with `[No LLM configured — showing retrieved context]`.

## Setting it

{% hint style="warning" %}
Set the variable on **both the backend and the Huey worker**. Deliveries, integrations and workflows run in the worker. Setting it on the backend only lets you save the URL, then the request fails in the background.
{% endhint %}

### Docker Compose

Add the line to the `environment` section of the `backend` and `huey` services, then restart them:

```yaml
services:
  backend:
    environment:
      - ALLOW_PRIVATE_NETWORK_REQUESTS=True
  huey:
    environment:
      - ALLOW_PRIVATE_NETWORK_REQUESTS=True
```

```bash
docker compose up -d
```

### Helm chart

The chart passes `backend.env` to the backend container only, and `backend.huey.env` to the Huey container. Set both:

```yaml
backend:
  env:
    - name: ALLOW_PRIVATE_NETWORK_REQUESTS
      value: "True"
  huey:
    env:
      - name: ALLOW_PRIVATE_NETWORK_REQUESTS
        value: "True"
```

## Security impact

The variable applies to the whole backend, not to one feature. Once set:

* every URL in the table above may point to any internal host, including the cloud metadata address, so any administrator who can change one of those URLs can make the backend reach internal services;
* most of these URLs are no longer required to use HTTPS. Keep them on HTTPS anyway. OAuth audit log sinks still require HTTPS, except on loopback.

To limit the exposure, keep the variable off unless you need it, and restrict the backend's and worker's outbound traffic to the hosts they need with a firewall, or with an `Egress` rule in the Helm chart's `networkPolicy`. The shared cache is not reachable this way: it listens on a unix socket, not a network port (see [Shared cache](shared-cache.md)).

When an HTTP(S) proxy is configured with `HTTP_PROXY` or `HTTPS_PROXY`, the backend connects to the proxy, not to the target, so the connection-level check does not apply: the proxy owns the outbound policy.
