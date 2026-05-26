---
description: Docker Compose or Helm for Kubernetes
---

# Quick start

## Config Builder

Customise the local deployment according to your needs:

{% embed url="https://youtube.com/live/VpUzN6GJrcs" %}

{% hint style="warning" %}
Make sure to have Docker 27 or above. If you get an error saying the `docker compose` command is not recognised, your Docker version is too old.
{% endhint %}

## Docker Compose

Make sure Docker and Docker Compose are installed on your system.

- clone the repo: `git clone https://github.com/intuitem/ciso-assistant-community.git`
- run the preparation script and follow the instructions: `./docker-compose.sh`

You can also find other variants for different setups as a starting point for your specific needs:

- [Remote / Virtualization](remote-virtualization.md)
- [Deploy on a VPS](vps.md)

## Helm chart

Make sure the Helm binary is installed and switch to your cluster context. The chart is published to a GitHub OCI registry — no `helm repo add` needed.

1. Pull the default values:
   ```sh
   helm show values oci://ghcr.io/intuitem/helm-charts/ce/ciso-assistant > custom.yaml
   ```
2. Edit `custom.yaml` for your environment. At minimum, look at:
   - `global.domain` — the hostname your instance will serve on.
   - `global.tls` and `ingress.tls.*` — enable TLS.
   - `backend.config.djangoSecretKey` — rotate from the default.
   - `backend.config.databaseType` (`sqlite`, `pgsql`, or `externalPgsql`) and the matching `postgresql.*` / `externalPgsql.*` block.
3. Create a namespace: `kubectl create ns ciso-assistant`
4. Install: `helm install ciso-assistant-release oci://ghcr.io/intuitem/helm-charts/ce/ciso-assistant -f custom.yaml -n ciso-assistant`

See [Helm Chart](helm-chart.md) for the full procedure (image tag pinning, values reference, and operational notes).

{% hint style="info" %}
This setup assumes Caddy will handle TLS on your behalf. If you experience SSL-related issues, you may need to patch your `ingress-nginx-controller` to enable the `enable-ssl-passthrough` flag.
{% endhint %}
