---
description: >-
  CISO Assistant can use memcached, an optional cache shared by all backend
  workers, to keep login rate limiting and other cached data consistent. This
  page explains how to enable it, how login rate limiting works, and how to set
  up your reverse proxy so each user is identified by their own IP address.
---

# Shared cache and login rate limiting

## Overview

The backend runs several worker processes (3 by default). By default, each worker keeps its own private cache in memory. Anything stored in the cache is then only seen by the worker that wrote it:

* **Rate limits are counted per worker.** With 3 workers, a limit of 5 failed logins becomes up to 15.
* **Changes can take time to reach every worker.** For example, a feature flag changed in the settings may still show its old value on the other workers for up to 30 seconds.

Memcached gives all workers, and the background worker (Huey), one cache to share. It is **optional and disabled by default**: if you enable it, you run one more container and are responsible for operating it.

The cache is used for:

* login rate limiting (see [below](#login-rate-limiting))
* the rate limit on inbound workflow webhooks
* feature flags
* locks that stop two workers from running the same metrics computation at the same time

## Enabling memcached

By default, the backend and Huey reach memcached through a **unix socket**, not over the network. Memcached has no authentication, and anything that can write to it can run code in the backend, because cached values are stored as Python pickles. With a socket, memcached has no network at all: only the containers that mount the socket can reach it, and no URL configured in CISO Assistant (webhook, SIEM, LLM...) can point at it. If several hosts or pods must share one memcached, see [memcached over TCP](#memcached-over-tcp).

### Docker Compose

`config/make_config.py` asks whether to run memcached. Answer **Yes** and the generated compose file includes everything below. The other provided compose files do not include memcached.

To add it to your own compose file:

```yaml
services:
  backend:
    environment:
      - ENABLE_MEMCACHED=True
    depends_on:
      memcached:
        condition: service_started
    volumes:
      - memcached_socket:/run/memcached

  huey:
    environment:
      - ENABLE_MEMCACHED=True
    depends_on:
      memcached:
        condition: service_started
    volumes:
      - memcached_socket:/run/memcached

  memcached:
    image: memcached:1.6-alpine
    restart: unless-stopped
    command: ["memcached", "-s", "/run/memcached/memcached.sock", "-a", "0700", "-m", "16"]
    network_mode: none
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    user: "1001:1001"
    volumes:
      - memcached_socket:/run/memcached

volumes:
  memcached_socket:
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: "uid=1001,gid=1001,mode=0700,size=64k"
```

The `memcached_socket` volume is a small RAM disk that only holds the socket. It belongs to user `1001`, the user the backend, Huey and memcached run as. Keep it that way: a plain named volume belongs to `root`, and memcached could not create its socket in it.

| Variable | Default | Description |
|---|---|---|
| `ENABLE_MEMCACHED` | `False` | Set to `True` on the **backend** and **huey** containers to use memcached. |
| `MEMCACHED_LOCATION` | `unix:/run/memcached/memcached.sock` | Where memcached listens: `unix:/absolute/path` or `/absolute/path` for a socket, `host:port` for [TCP](#memcached-over-tcp). Keep the default with the setup above. A relative socket path is read as a host name. |

{% hint style="warning" %}
Set `ENABLE_MEMCACHED=True` on **both** the backend **and** huey containers. Without it, each worker keeps using its own private cache, and no error or warning is shown.
{% endhint %}

{% hint style="warning" %}
Keep the socket unless you need [memcached over TCP](#memcached-over-tcp). The socket is what keeps memcached out of reach of everything but the backend and Huey. Never publish a memcached port.
{% endhint %}

The `-m 16` option gives memcached 16 MB of memory. The cache holds rate limit counters, feature flags, short-lived OAuth codes and copies of small API responses.

### Helm chart

Set `memcached.enabled: true` to run memcached as an extra container in the backend pod. The backend, Huey and memcached share its socket through a memory-backed `emptyDir` volume:

```yaml
memcached:
  enabled: true      # sets ENABLE_MEMCACHED on the backend and huey containers
  memoryLimit: 16    # in MB
```

{% hint style="warning" %}
Each backend pod has its own memcached. If you set `backend.replicas` above 1, the pods do **not** share their cache, and rate limits are multiplied by the number of pods. To share one cache between pods, run memcached yourself and reach it [over TCP](#memcached-over-tcp).
{% endhint %}

### memcached over TCP

Several backend hosts or pods can only share one memcached over the network. Run memcached as its own service, and set `ENABLE_MEMCACHED=True` and `MEMCACHED_LOCATION` to its address (for example `memcached:11211`) on the backend and Huey. With the Helm chart, leave `memcached.enabled` at `false` and set both variables in `backend.env` and `backend.huey.env`.

{% hint style="danger" %}
Anything that can connect to memcached can run code in the backend. Over TCP, only your network filtering keeps others out:

* Allow only the backend and Huey to connect to memcached, for example with a Kubernetes NetworkPolicy or a dedicated internal network. Never publish its port.
* The backend's own outbound requests (webhooks, SIEM, LLM...) are refused for private addresses unless `ALLOW_PRIVATE_NETWORK_REQUESTS` is set. With it set, they can reach memcached too.
{% endhint %}

## Login rate limiting

CISO Assistant limits login attempts to slow down password-guessing attacks. The limits apply to local (email and password) logins. By default:

| Limit | What happens |
|---|---|
| **5 failed logins for the same email in 5 minutes** | This account is locked for 5 minutes, **even with the correct password**. Other accounts are not affected. |
| **10 failed logins from the same IP address in 1 minute** | Logins from this IP address are blocked for the rest of the minute. |
| **30 login attempts from the same IP address in 1 minute** | Logins from this IP address are blocked for the rest of the minute. Successful attempts count too. |

Without memcached, each worker counts on its own, so the effective limits are higher (see [Overview](#overview)).

A successful login does not count as a failure. When a limit is reached, the login page shows:

> Too many login attempts. Please try again later.

The block lifts by itself when the time window ends. To clear all limits at once, for example after a test, restart memcached, or the backend if you do not use memcached:

```bash
docker compose restart memcached
```

### Changing the limits

Set these variables on the **backend** container:

| Variable | Default | What it limits |
|---|---|---|
| `LOGIN_FAILED_RATE_LIMIT` | `10/m/ip,5/5m/key` | Failed logins and wrong second-factor (MFA) codes, per IP address (`ip`) and per account (`key`) |
| `LOGIN_RATE_LIMIT` | `30/m/ip` | All login attempts, per IP address |

A value is a comma-separated list of rules written `amount/period/per`:

* `amount` is the number of attempts allowed in the period.
* `period` is `s`, `m`, `h` or `d`, optionally preceded by a number: `5m` means 5 minutes.
* `per` is `ip`, or `key` for the email (failed logins only). It defaults to `ip`.

An empty value turns that limit off. If a value is malformed, the backend does not start, and its logs name the variable.

For example, to keep the per-IP limit but remove the per-email lockout, so that knowing an email is not enough to lock its account:

```yaml
services:
  backend:
    environment:
      - LOGIN_FAILED_RATE_LIMIT=10/m/ip
```

The account is then no longer protected against password guessing spread over many IP addresses. The same goes for second-factor codes, for anyone who already has the password: without a `key` rule they are limited only per IP address, and an empty value removes their limit entirely.

With the Helm chart, set the variables through `backend.env`:

```yaml
backend:
  env:
    - name: LOGIN_FAILED_RATE_LIMIT
      value: "10/m/ip"
```

## Reverse proxy and client IP address

The per-IP limits need to know each user's real IP address. With the default setup, every request passes through a reverse proxy (Caddy, Traefik, BunkerWeb...). If the IP address is not passed on correctly, all users appear to come from the proxy, and **10 wrong passwords from anyone block logins for everyone**.

The real IP address is passed on in the `X-Forwarded-For` header:

1. The **reverse proxy** adds the client IP address to `X-Forwarded-For`. Caddy, Traefik and Apache do this by default.
2. The **frontend** reads the client IP address from that header. Set these variables on the frontend container:

   | Variable | Value | Description |
   |---|---|---|
   | `ADDRESS_HEADER` | `x-forwarded-for` | Header that holds the client IP address. |
   | `XFF_DEPTH` | `1` | Number of reverse proxies in front of the frontend. |

   The frontend then passes the IP address on to the backend.
3. The **backend** uses the **last** entry of `X-Forwarded-For`, which is the one added by the proxy just in front of it.

{% hint style="warning" %}
This works when there is **exactly one** reverse proxy in front of the backend:

* **Do not expose the backend port (8000) directly.** A client that reaches the backend without the proxy can send a fake `X-Forwarded-For` and get past the per-IP limits. The per-email limit still applies.
* **Avoid a second proxy (such as a load balancer) in front of your reverse proxy**, unless it is set up to pass the real client IP address on. Otherwise all users share the load balancer's IP address.
{% endhint %}

With the Helm chart, `ADDRESS_HEADER` and `XFF_DEPTH` are set on the frontend only when `ingress.enabled` is `true`. Use `frontend.config.xffDepth` to change the number of proxies. If you use your own ingress instead, set both variables yourself through `frontend.env`.

The same IP address is recorded in the [audit log](../features/audit-log.md) (`remote_addr`).

Every failed login is logged as `Failed login attempt`, with the email and the IP address, and recorded in the audit log as *Login failed*. Failed logins have their own cap in the audit log (`AUDITLOG_MAX_RECORDS`, like other entries), so a flood of them cannot push other entries out.

Logins refused by these limits are logged too, squashed so that an attack does not flood the logs: a `Logins refused by rate limit` warning with the IP address or the email and the number of refusals, at the 2nd, 4th, 8th... refusal and at least every 5 minutes while refusals go on. Counts restart 1 hour after the first refusal. A single refusal is not logged.

## Troubleshooting

### Nobody can log in, but everything else works

If you enabled memcached and it is stopped or stuck, the backend keeps working without it, but every login is refused with "Too many login attempts. Please try again later.", even with the correct password. Login rate limiting cannot count attempts without memcached, so it refuses them rather than letting them through. Users who are already logged in can keep working, except for actions that ask for their password or second factor again (such as managing MFA). Applications that sign in through CISO Assistant as an OAuth provider cannot complete their sign-in. The backend health check (`/api/health/`) still reports the backend as healthy.

While memcached is down, metric computations are skipped or postponed, and the rate limits of inbound webhooks and of the chat assistant are not applied.

Check that memcached is running and start it again if needed:

```bash
docker compose ps memcached
docker compose up -d memcached
```

Logins work again within about 10 seconds of memcached being back, without restarting the backend.

### All users are blocked at the same time

The backend probably sees the same IP address for every user. Check the `ip` field in the backend logs:

```bash
docker compose logs backend | grep auth/login
```

If every line shows the same internal address (for example `172.x.x.x`), check the [reverse proxy setup](#reverse-proxy-and-client-ip-address): `ADDRESS_HEADER` and `XFF_DEPTH` on the frontend, and `X-Forwarded-For` on your proxy.

Until the setup is fixed, you can turn the per-IP limits off and keep only the per-email one: set `LOGIN_FAILED_RATE_LIMIT=5/5m/key` and leave `LOGIN_RATE_LIMIT` empty (see [Changing the limits](#changing-the-limits)).

### Limits seem higher than documented

Memcached is probably not in use, so each worker counts on its own. This is expected if you did not enable it. Otherwise, check that `ENABLE_MEMCACHED=True` is set on the backend container:

```bash
docker compose exec backend env | grep MEMCACHED
```
