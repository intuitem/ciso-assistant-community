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



Make sure to have Helm binary installed and switch to your cluster context.

1. add the helm repository

`helm repo add intuitem https://intuitem.github.io/ca-helm-chart/`

2. get the default values&#x20;

`helm show values intuitem/ciso-assistant > my-values.yaml`

3. check and adjust them to your needs, specifically the `frontendOrigin` parameter&#x20;
4. create a namesapce for your deployment&#x20;

`kubectl create ns ciso-assistant`

5. install&#x20;

`helm install my-octopus intuitem/ciso-assistant -f my-values.yaml -n ciso-assistant`





{% hint style="info" %}
This setup is based on the fact that Caddy will handle the TLS on your behalf. In case you're experiencing ssl related issues, you might want to patch your ingress-nginx-controller to activate the `enable-ssl-passthrough` flag.
{% endhint %}



In case you are running it locally with a non reachable FQDN, you might want to consider adding  `tls internal` on the Caddy config for self-signed certificate.
