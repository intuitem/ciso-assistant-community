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

The in-product AI assistant needs two things wired in the chart: the `ENABLE_CHAT` flag on the backend and a reachable [Qdrant](https://qdrant.tech/) vector database for retrieval-augmented generation. Setting `qdrant.enabled: true` deploys the official [Qdrant chart](https://github.com/qdrant/qdrant-helm) as a dependency (a StatefulSet with persistent storage and health probes) and injects `QDRANT_URL` automatically.

```yaml
backend:
  config:
    chat:
      enabled: true        # sets ENABLE_CHAT on the backend and Huey worker
qdrant:
  enabled: true            # deploys the Qdrant subchart and injects QDRANT_URL
```

Notes:

- Any key under `qdrant:` is passed through to the Qdrant subchart (e.g. `qdrant.persistence.size`, `qdrant.resources`). Persistence is on by default; see the [subchart values](https://github.com/qdrant/qdrant-helm/tree/main/charts/qdrant) for all options.
- The Qdrant subchart is bundled inside the published chart, so installing needs no access to the Qdrant Helm repo. Air-gapped clusters still pull the **Qdrant image** at runtime: mirror it and override `qdrant.image.repository` (same as for the backend/frontend images).
- To point at an **external** Qdrant instead of the bundled one, leave `qdrant.enabled: false` and set `QDRANT_URL` through `backend.env` and `backend.huey.env`.
- The **LLM provider** (Ollama or any OpenAI-compatible endpoint, model, base URL) is configured from the in-app **Settings → Chat/AI** section, not from the chart. LLM inference is heavy; point it at a GPU-backed endpoint.
- The Qdrant collection and the indexes are **not** created automatically. After the pods are up, run the indexing commands once from the backend pod (`init_qdrant` creates the collection, `index_objects` indexes your existing risk/control/asset records, `index_libraries` indexes the framework libraries):

  ```sh
  POD="deploy/ciso-assistant-release-backend"
  kubectl exec -n ciso-assistant $POD -c backend -- uv run python manage.py init_qdrant
  kubectl exec -n ciso-assistant $POD -c backend -- uv run python manage.py index_objects
  kubectl exec -n ciso-assistant $POD -c backend -- uv run python manage.py index_libraries --sync
  ```

## Custom CA certificates

If your pods need to trust an internal CA (for SMTP, SSO, or any outbound TLS service signed by a private authority), provide **just your CA** in a secret. Trust is added on top of the default roots, not replaced, so public CAs keep working:

- Backend and Huey (Python): an init container concatenates the system CA bundle with your CA into a shared bundle, and `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` point at it.
- Frontend (Node): `NODE_EXTRA_CA_CERTS` points at your CA, which Node adds to its built-in roots.

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

The backend init container writes the merged bundle to an `emptyDir`. If you also harden the pod to run as a non-root user (`global.securityContext.runAsNonRoot` / per-component `runAsUser`), set an `fsGroup` so that user can write the volume:

```yaml
global:
  securityContext:
    fsGroup: 1001
```

## Network policy

To restrict pod traffic, enable the bundled `NetworkPolicy` and pass your own ingress/egress rules. The policy selects all pods of the release by default, so your rules must also allow the **internal** flows the app relies on: the frontend BFF calls the backend (`PUBLIC_BACKEND_API_URL`) server-side, and the backend reaches Qdrant. Forgetting these blocks the app even though the ingress controller can reach it.

Replace `ciso-assistant-release` below with your Helm release name.

```yaml
networkPolicy:
  enabled: true
  policyTypes:
    - Ingress
  ingress:
    # internal traffic between CISO Assistant pods (frontend -> backend, backend -> qdrant)
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/instance: ciso-assistant-release
    # the ingress controller reaching the frontend and backend
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

Chart upgrades are normally additive: new capabilities ship as new values keys, and existing keys are not removed or renamed within a major chart version, so your current `custom.yaml` keeps working as-is. New features are **opt-in and off by default** — if you don't set their keys, nothing changes in that area.

When a breaking change to the values shape is unavoidable, it is released under a new **major chart version** and the required migration steps are documented in the release notes. Read them before upgrading across a major version.

The main thing to manage on upgrade is the **application version**. If you did not pin `global.image.tag`, the images move to the chart's `appVersion` on the next `helm upgrade`. Pin the tag to the version you tested and review the [release notes](https://github.com/intuitem/ciso-assistant-community/releases) for the range you're crossing. Database migrations run automatically on backend startup, so no manual schema step is needed.

## Uninstall

```sh
helm uninstall ciso-assistant-release -n ciso-assistant
```

PostgreSQL persistent volumes are **not** deleted automatically when using the bundled subchart. Inspect with `kubectl get pvc -n ciso-assistant` and remove manually if you want a clean slate.

## Legacy

> **Note:** The old Helm repository (`intuitem.github.io/ca-helm-chart`) is no longer maintained. The values shape changed substantially between the legacy `charts/ciso-assistant/` chart and the current `charts/ciso-assistant-next/` chart (`frontendOrigin` → `global.domain`, no `clientName`/`clusterDomain` shorthand, separate ingress block). New installs should use the OCI registry above.
