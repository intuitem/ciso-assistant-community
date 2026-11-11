# Optional memcached shared cache, reached over a unix socket

- Status: Accepted
- Deciders: @monsieurswag @ericintuitem

## Context

The backend runs several gunicorn worker processes, and Huey runs in its own process. Each process has its own memory, so Django's default cache (local memory) is private to the process that wrote it. A request may land on any worker.

Every cached value is therefore per process. allauth's login rate limits count per worker, so 3 workers triple every limit. A feature flag changed in the settings reaches the other workers only when their cached copy expires (30 seconds). The locks that stop two metrics computations from running at once only work inside one process.

## Decision

We will support memcached as an optional shared Django cache, disabled by default and enabled with `ENABLE_MEMCACHED=True` on the backend and Huey. When enabled, they reach memcached through a unix socket (`MEMCACHED_LOCATION`, default `unix:/run/memcached/memcached.sock`), and memcached gets no network: `network_mode: none` in Compose, a sidecar with no port in the Helm chart. The Compose configurator asks whether to run it; the chart has `memcached.enabled` (default `false`). Operators may point `MEMCACHED_LOCATION` at a TCP address instead, for example to share one memcached between pods; the docs say what network filtering this needs.

## Consequences

- Without memcached, behaviour is unchanged: caches stay per process.
- Whoever enables memcached runs it. If it stops, requests that use the cache fail until it is back, while the backend health check stays green.
- Code must stay correct with a per-process cache. Use the cache for rate limits, locks and short-lived copies of data, never as the only copy.
- Never store secrets, sessions or tokens in the cache.
- Never mount the socket into another container. Whoever switches memcached to TCP must filter the network so that only the backend and Huey reach it.
- The chart's memcached is per pod: with several backend replicas, rate limits count per pod, unless the operator runs a shared memcached over TCP.

## Security

Memcached has no authentication, and Django stores cached values as pickles, so anyone who can write to memcached can run code in the backend. With the default socket setup, the risk is low because nothing but the backend and Huey can reach it:

- **No network listener.** memcached started with `-s` opens no TCP or UDP port, and its container has no network (`network_mode: none`). No other container, host or pod can connect to it.
- **No SSRF path.** Every outbound request the backend makes to a configured URL (webhooks, audit sinks, LLM, Jira, ServiceNow, mail server) targets a host and port. A unix socket cannot be named that way. This holds even where `ALLOW_PRIVATE_NETWORK_REQUESTS` turns off the SSRF guard (`core/net_safety.py`), and without relying on memcached's own refusal of HTTP request lines.
- **Only the cache's own users mount the socket.** In Compose, the socket volume is owned by uid 1001 with mode 0700 and is mounted only into the backend, Huey and memcached. In the chart, it is an `emptyDir` private to the backend pod, mounted into the same three containers. The frontend never mounts it.

Accepted residual risks: code running in the backend or Huey can write to memcached, but it already holds the database credentials. The rate-limit counters, feature flags and locks in the cache are not sensitive. An operator can switch memcached to TCP: the docs say what network filtering it needs, and that filtering is the operator's responsibility.

What would reopen this assessment: shipping memcached over TCP in our own Compose files or chart, mounting its socket into another container, or caching secrets or session data.
