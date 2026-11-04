# Title stating the decision, not the topic

- Status: Accepted
- Deciders: @monsieurswag @ericintuitem

## Context

In most deployments the backend runs inside multiple gunicorn worker processes.
A request may be dispatched to any one of them, and each one of them have their own memory (and therefore their own python variables).
If a request is dispatched to WORKER 1 and update its cache, the next request may be dispatch to WORKER 2 whose cache will not have received this update (as it's a separated cache in memory).

Any form of caching in the application is therefore currently an inconsistent cache.
For example it impacts allauth rate limiting (by tripling all its rate limits if we have 3 gunicorn worker being deployed).
There may also be problems related to oauth flows/MCP requests which handlers rely on information stored in RAM (and persisting across requests).

## Decision

We will use memcached as a sidecar container for caching, the django cache will be configured to use memcached.
This will be optional (django won't use it unless the `ENABLE_MEMCACHED` env variable ie set), although strictly required for serious deployments.

## Consequences

In production, the cache will now be consistent.
This will prevent a whole class of bugs related to inconsistent caching (as long we use django cache when required).
This will also give us some more potential and confidence for implementing cache-based performance optimizations in the future.

## Security considerations

For now memcached (as used in production) is only accessible via TCP, accessing memcached without perfoming some RCE in the frontend/backend isn't possible (unless memcached TCP server is exposed which won't be the case in both docker-compose/k8s deployments).

So there isn't much security risks involved by using it anyway.

## Alternatives considered

- Making our own cache: Less safe/more maintenance
- Using DB-based cache: Too slow (this would make most cache-based optimizations useless).
- Using redis: More complex with no benefit (no redis-specific feature will ever be required for us).
