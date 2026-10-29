
# Back the login rate limiting with a shared in-memory database

- Status: Proposed
- Date: 2026-10-29
- Deciders: @monsieurswag

## Context

The `django-allauth` rate limiting uses `django.core.cache` which is basic in-memory cache.
In production (whether it's SaaS/on-premise) we use gunicorn which creates multiple worker process where each one have their own RAM space.
This means each worker process has its own django cache with its own values, this causes 2 problems:
- Cached values are duplicated (they use `N` times more RAM than normal, with `N` being the number of gunicorn worker processes)
- The caches are inconsistent (2 request can return different result due to different worker processes having 2 different values in their cache).

This problem of cache duplication/incosistency is something that already caused problems in the past when the `RequirementMappingSet` objects were loaded/modified in RAM.

## Decision

Gunicorn worker processes will elect a leader (using a `flock`-based leader election).
The leader worker process will create a new OS thread(the leader thread) which will open a UNIX socket with a minimal RPC server.
This will allow all gunicorn processes to be able to execute code/fetch values from a common place.
The first usage of this mechanism will be for the IP-based rate-limiting (the leader thread will store the rate-limiting counters in its RAM).

Both the `.lock` leader election file and the unix socket will be stored in `/tmp` (as it's the best place for linux/mac OS/docker/kubernetes environment interoperability).

## Consequences

Shared(non-duplicated) consistent in-memory cache is now possible (as we had our own memcached/redis).
IP-based rate limiting is now consistent.

## Security considerations

### IP-based rate limiting:

This rate-limiting system is effective against bruteforce attacks on a large number of accounts (being the most common form of bruteforce).
However if has 2 downsides (which can be fixed/reduced by a future complementary per-account rate limiting):
- A bruteforce targeting a specific account isn't well protected.
- A user can block other users (sharing the same IP address) for a few minutes by failing its login too many times.

So a per-account rate limiting should be implemented in the near future.

### X-Forwaded-For trust:

The rate-limiting system always trust the ip address passed in the `X-Forwaded-For` header, which can lead to IP spoofing (and therefore rate-limiting bypass) if the API is directly accessible (without a reverse proxy setting/tampering the `X-Forwaded-For` header).

This was accepted as an (unencrypted)HTTP-based API isn't secured anyway, and the only way to make it secure(HTTPS) is to have a reverse proxy which, by itself, already counter IP spoofing (by changing the `X-Forwaded-For` header).

The `XFF_DEPTH=1` frontend env variable make it so only the last entry of the `X-Forwaded-For` header is used (so an IP injected by an attacker would never be read by the backend anyway).

Casual local-only users shouldn't be impacted by rate-limiting anyway as they have complete control over it (restarting the server reset it + they can disable it + the probability of them being rate-limited is very low anyway).

## Alternatives considered

- **Using a disk-based django cache**: (Using `django.core.cache.backends.db.DatabaseCache`) is the easiest fix, but disk-based caching is obviously bad performance-wise + it doesn't fix the fact that we can't have any consistent shared in-memory state.
- **A dedicated `LoginAttempt` model**: not flexible enough, creating a new model dedicated each time we have a new kind of value we need to cache (in a non-duplicated/consistent way) would be bad.
- **Using Redis/Memcached**: functionally overkill(we don't need this much functionalities), significant extra resource utilization, would reduce the installability/adaptability of the application (imagine having to start a whole separate service just make ciso-assistant work locally).
- **Run a single gunicorn process**: limit the throughput (which is already bad enough with a non-async python backend).
