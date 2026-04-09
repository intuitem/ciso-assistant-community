---
description: instructions for Kubernetes installation with Helm Chart
---

# Helm Chart

### GH OCI registry

1. Getting the values&#x20;

```sh
helm show values oci://ghcr.io/intuitem/helm-charts/ce/ciso-assistant > custom.yaml
```

2. customize as you see fit
3. Install the chart

```sh
helm install ciso-assistant-release oci://ghcr.io/intuitem/helm-charts/ce/ciso-assistant -f custom.yaml
```

### Legacy

> **Note:** The old Helm repository (`intuitem.github.io/ca-helm-chart`) is no longer maintained. Please use the OCI registry above for new installations.&#x20;



