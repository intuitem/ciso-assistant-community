---
description: How to add custom certificates for your remote installation
---

# Custom certificates

You can configure your own Certificate by replacing the line `tls internal` in the docker-compose.yml by `tls <cert_file> <key_file>`. Here is Caddy documentation on this [https://caddyserver.com/docs/caddyfile/directives/tls](https://caddyserver.com/docs/caddyfile/directives/tls)

\
Before doing this, there is just one step, you need to add the `cert_file` and the `key_file` inside caddy container.

You have basically two ways to do it:

* Adding the two files inside `caddy_data` directory, as it is already mounted by default in the volumes, and specify the path to the files:&#x20;

```yaml
caddy:
    container_name: caddy
    image: caddy:2.10.0
    ...
    volumes:
      - ./caddy_data:/data
    command: |
      sh -c 'echo $$CISO_ASSISTANT_URL "{
      reverse_proxy /api/* backend:8000
      reverse_proxy /* frontend:3000
      tls data/<path>/cert_file data/<path>/key_file
      }" > Caddyfile && caddy run'
```

* If you don’t have this volume or you want to add another, create a repository at the same level of your docker compose file for example `/certs`, add the files inside and moun it:

```yaml
caddy:
    container_name: caddy
    image: caddy:2.10.0
    ...
    volumes:
      - ./caddy_data:/data
      - ./certs:/certs
    command: |
      sh -c 'echo $$CISO_ASSISTANT_URL "{
      reverse_proxy /api/* backend:8000
      reverse_proxy /* frontend:3000
      tls certs/cert_file certs/key_file
      }" > Caddyfile && caddy run'
```
