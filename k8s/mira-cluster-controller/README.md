# MIRA Cluster controller

MIRA cluster controller is a Django application aimed to control within a K8s cluster the deployement of objects for each client.

Caddy is managing the TLS connection to the controller.

A client is defined by a name and an administrator email.

When a client is created, the following objects are created (or updated if the objects already exist):
- a service
- an ingress
- a statefulset

The objects are defined in a templated yaml, that is stored in a configmap. This allows for updating the template without changing the controller.

When a new version of Mira is released, the template shall be updated, and each client can be updated by "saving" it without change.

When a client is deleted, corresponding objects are destroyed. The PersistentVolumeClaim is not deleted automatically, so recreating a client will retrieve existing data. To delete the PVC, used kubectl directly.

Clients objects are created in the "default" namespace.

## Installation

The namespace "controller" shall be created to host the controller:

```shell
kubectl create namespace controller
````

The following files are used to deploy the application:

Name                                       | Content
-------------------------------------------|------------------------------------
serviceaccounts.controller.yaml            | Definition of a service account for the controller 
role.controller.yaml                       | Access rights for the controller (in default namespace)
svc.mira-cluster-controller.yaml           | Service for the controller
ing.mira-cluster-controller.yaml           | Ingress for the controller
sts.mira-cluster-controller.yaml           | StatefulSet for the controller
cm.mira-cluster-controller-config-dev.yaml | Parameters for the controller

A loadbalancer is also required. Its setup depends on the cloud provider. For Scaleway, please have a look to the corresponding readme file.

## Environment variables

Environment variables come from the "mira-cluster-controller-config" configmap.

Name                  | value                           | example
----------------------|---------------------------------|--------------
DJANGO_DEBUG          | debug mode                      | "True"
CLUSTER_CONTROLLER_URL| url to reach the controller     | "https://caudron.alsigo.net"
CLUSTER_DOMAIN        | domain to append to client name | "alsigo.net"


See cm.mira-cluster-controller-config-dev.yaml for an example.

## Client templates, config and secrets

The template yaml file for client objects creation is stored in the configmap "templates-yaml". To create it, use:

```shell
kubectl create configmap -n controller templates-yaml --from-file=templates/client_template.yaml
````

The configuration is stored in the mira-config configmap. To create nstall it, use:

```shell
kubectl apply -f cm.mira-config.yaml
````

For recaptcha v2 private key, create the "recaptcha" secret with the following command:
```shell
kubectl create secret generic recaptcha -n default --from-literal=RECAPTCHA_PRIVATE_KEY=XXX
```

For SMTP passwords, create the "smtp-out" secret with the following command:
```shell
kubectl create secret generic smtp-out -n default --from-literal=EMAIL_HOST_PASSWORD=XXX --from-literal=EMAIL_HOST_PASSWORD_RESCUE=XXX
```

## Observability

Installing Prometheus and Grafana is recommended.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add stable https://kubernetes-charts.storage.googleapis.com/
helm repo add stable "https://charts.helm.sh/stable" 
helm repo update
helm install prometheus prometheus-community/prometheus --create-namespace --namespace monitoring  --set server.persistentVolume.size=100Gi,server.retention=30d
helm install prometheus prometheus-community/prometheus --create-namespace --namespace monitoring  --set server.persistentVolume.size=100Gi,server.retention=30d
# export POD_NAME=$(kubectl get pods --namespace monitoring -l "app=prometheus,component=server" -o jsonpath="{.items[0].ta.name}")
# kubectl --namespace monitoring port-forward $POD_NAME 9090
helm repo add grafana https://grafana.github.io/helm-charts
helm install grafana grafana/grafana --set persistence.enabled=true,persistence.type=pvc,tence.size=10Gi --namespace=monitoring
kubectl get secret --namespace monitoring grafana -o jsonpath="{.data.admin-password}" | base64 --decode ; echo
kubectl port-forward --namespace monitoring service/grafana 3000:80
```

In Grafana, add the Prometheus data source with path "http://prometheus-server".

## Tips

To list all pods and their current version:

```shell
kubectl get pods -n default -o jsonpath='{range .items[*]}{@.metadata.name}{" "}{@.spec.containers[*].image}{"\n"}{end}'| column -t
```

## MIRA version update

- push the new image
- adjust the template file
  - either delete it and replace it
  - or edit it (kubectl edit cm templates-yaml) and simply change the version
- For each client, do a save in the controller GUI. This will provoke the update
- Use the command given in tips to list all pods and check the current version
