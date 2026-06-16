---
description: Kubernetes installation with the official Helm chart
---

# Helm Chart

The chart lives at `oci://ghcr.io/intuitem/helm-charts/ce/ciso-assistant`. Source: [`charts/ciso-assistant-next/`](https://github.com/intuitem/ciso-assistant-community/tree/main/charts/ciso-assistant-next) in the repo.

## Prerequisites

- A Kubernetes cluster you have admin access to.
- `helm` 3.8+ (OCI registries require 3.8 or newer).
- `kubectl` configured for the target cluster.
- An ingress controller if you want to expose the app externally.
- A persistent storage class (defaults work on most managed clusters).

## Install

1. **Pull the default values** into a working file:

   ```sh
   helm show values oci://ghcr.io/intuitem/helm-charts/ce/ciso-assistant > custom.yaml
   ```

2. **Customise** `custom.yaml`. The most important settings:

   - `global.domain` — the hostname your instance will serve on.
   - `global.tls` — set to `true` if you're serving over HTTPS.
   - `ingress.enabled` and `ingress.tls.*` — enable + configure the ingress.
   - `backend.config.djangoSecretKey` — **rotate from the default `changeme`**.
   - `backend.config.databaseType` — `sqlite` (default, single-pod), `pgsql` (bundled PostgreSQL via Bitnami subchart), or `externalPgsql`.
   - `postgresql.*` — when using the bundled PostgreSQL.
   - `externalPgsql.*` — when pointing at your own PostgreSQL instance.
   - `backend.config.smtp.*` — outgoing email configuration.

   The chart README in the repository carries the full values table (`charts/ciso-assistant-next/README.md`) — refer to it for every key with its default and description.

3. **Pin the appVersion** to a published release if you want predictable upgrades. Set `global.image.tag` in `custom.yaml` to the version you tested against (e.g. `v3.18.1`). Leaving it empty pins to the chart's `appVersion`, which moves with the chart.

4. **Create a namespace and install**:

   ```sh
   kubectl create ns ciso-assistant
   helm install ciso-assistant-release oci://ghcr.io/intuitem/helm-charts/ce/ciso-assistant \
     -f custom.yaml \
     -n ciso-assistant
   ```

## Verify

```sh
kubectl get pods -n ciso-assistant
kubectl get ingress -n ciso-assistant
```

The backend pod runs migrations on startup; allow it ~30s before checking the frontend.

## AI assistant (chat / RAG)

The in-product AI assistant needs two things wired in the chart: the `ENABLE_CHAT` flag on the backend and a reachable [Qdrant](https://qdrant.tech/) vector database for retrieval-augmented generation.

```yaml
backend:
  config:
    chat:
      enabled: true        # sets ENABLE_CHAT on the backend and Huey worker
qdrant:
  enabled: true            # deploys a bundled Qdrant and injects QDRANT_URL
  persistence:
    enabled: true          # otherwise storage is ephemeral (emptyDir)
```

Notes:

- To point at an **external** Qdrant instead of the bundled one, leave `qdrant.enabled: false` and set `QDRANT_URL` through `backend.env` and `backend.huey.env`.
- The **LLM provider** (Ollama or any OpenAI-compatible endpoint, model, base URL) is configured from the in-app **Settings → Chat/AI** section, not from the chart. LLM inference is heavy; point it at a GPU-backed endpoint.
- The Qdrant collection and the indexes are **not** created automatically. After the pods are up, run the indexing commands once from the backend pod:

  ```sh
  kubectl exec -n ciso-assistant deploy/ciso-assistant-release-backend -c backend -- \
    python manage.py init_qdrant
  kubectl exec -n ciso-assistant deploy/ciso-assistant-release-backend -c backend -- \
    python manage.py index_libraries --sync
  ```

## Custom CA certificates

If your pods need to trust an internal CA (for SMTP, SSO, or any outbound TLS service signed by a private authority), mount the certificate from an existing secret on all pods. The chart wires both trust stores: `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` (Python backend and Huey) and `NODE_EXTRA_CA_CERTS` (Node frontend).

```sh
kubectl create secret generic my-ca -n ciso-assistant --from-file=ca.crt=./internal-ca.crt
```

```yaml
global:
  extraCerts:
    enabled: true
    secretName: my-ca
    fileName: ca.crt
    mountPath: /etc/ssl/extra-certs
```

## Network policy

To restrict pod traffic, enable the bundled `NetworkPolicy` and pass your own ingress/egress rules. The policy selects all pods of the release by default.

```yaml
networkPolicy:
  enabled: true
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
```

## Upgrade

```sh
helm upgrade ciso-assistant-release oci://ghcr.io/intuitem/helm-charts/ce/ciso-assistant \
  -f custom.yaml \
  -n ciso-assistant
```

If you pinned `global.image.tag`, bump it in `custom.yaml` before running `upgrade`. Without a pin, the deployment will pick up whichever appVersion the chart points to.

## Uninstall

```sh
helm uninstall ciso-assistant-release -n ciso-assistant
```

PostgreSQL persistent volumes are **not** deleted automatically when using the bundled subchart. Inspect with `kubectl get pvc -n ciso-assistant` and remove manually if you want a clean slate.

## Legacy

> **Note:** The old Helm repository (`intuitem.github.io/ca-helm-chart`) is no longer maintained. The values shape changed substantially between the legacy `charts/ciso-assistant/` chart and the current `charts/ciso-assistant-next/` chart (`frontendOrigin` → `global.domain`, no `clientName`/`clusterDomain` shorthand, separate ingress block). New installs should use the OCI registry above.
