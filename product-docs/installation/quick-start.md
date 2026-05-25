---
description: Docker Compose or Helm for Kubernetes
---

# Quick start

### Config Builder

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

Make sure the Helm binary is installed and switch to your cluster context.

1. Add the Helm repository: `helm repo add intuitem https://intuitem.github.io/ca-helm-chart/`
2. Get the default values: `helm show values intuitem/ciso-assistant > my-values.yaml`
3. Check and adjust them to your needs, in particular the `frontendOrigin` parameter.
4. Create a namespace for your deployment: `kubectl create ns ciso-assistant`
5. Install: `helm install my-octopus intuitem/ciso-assistant -f my-values.yaml -n ciso-assistant`

{% hint style="info" %}
This setup assumes Caddy will handle TLS on your behalf. If you experience SSL-related issues, you may need to patch your `ingress-nginx-controller` to enable the `enable-ssl-passthrough` flag.
{% endhint %}
