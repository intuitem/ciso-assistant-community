# MIRA Cluster controller

MIRA cluster controller is a Django application aimed to control within a K8s cluster the deployement of objects for each client.

## Installation

Use sts.mira-cluster-controller.yaml to push the application on the cluster.

## Environment variables

Environment variables come from the "mira-cluster-controller-config" configmap.

See cm.mira-cluster-controller-config-dev.yaml for an example.

The template yaml file for client objects creation is stored in the configmap "templates". To create it, use:
```shell
kubectl create configmap templates-yaml --from-file=templates/client_template.yaml
````
