from django.db import models
from kubernetes import client, config


def create_service(core_v1_api, client_name):
    body = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(
            name=f"svc-{client_name}"
        ),
        spec=client.V1ServiceSpec(
            selector={f"client": client_name},
            cluster_ip="None",
            type="ClusterIP",
            ports=[
                client.V1ServicePort(port=80,target_port=80),
                client.V1ServicePort(port=443,target_port=443),
            ]
        )
    )
    core_v1_api.create_namespaced_service(namespace="default", body=body)


def create_stateful_set_object(client_name):
    container = client.V1Container(
        name=f"sts-{client_name}",
        image="mira:latest",
        image_pull_policy="IfNotPresent",
        ports=[client.V1ContainerPort(container_port=443)],
    )
    # Template
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={
                "app": "mira",
                "client": client_name
            }
        ),
        spec=client.V1PodSpec(containers=[container]))
    # Spec
    spec = client.V1StatefulSetSpec(
        replicas=1,
        service_name=f"svc-{client_name}",
        selector=client.V1LabelSelector(
            match_labels={"app": "mira"}
        ),
        template=template)
    # StatefulSet
    statefulset = client.V1StatefulSet(
        api_version="apps/v1",
        kind="StatefulSet",
        metadata=client.V1ObjectMeta(name=f"sts-(client_name)"),
        spec=spec)

    return statefulset


def create_stateful_set(apps_v1_api, stateful_set_object):
    # Create the Statefulset in default namespace
    # You can replace the namespace with you have created
    apps_v1_api.create_namespaced_stateful_set(
        namespace="default", body=stateful_set_object
    )


class Client(models.Model):
    name = models.CharField(max_length=40)
    admin_email = models.EmailField()

    core_v1_api = None
    apps_v1_api = None
    try:
        config.load_incluster_config()
        core_v1_api = client.CoreV1Api()
        apps_v1_api = client.AppsV1Api()
    except:
        print("not in cluster")

    def save(self, *args, **kwargs):
        print("saving", self.name, self.admin_email)
        super().save(*args, **kwargs)  # Call the "real" save() method.
        print("creating k8s objects for", self.name)
        create_service(self.core_v1_api, self.name)
        create_stateful_set(self.apps_v1_api, create_stateful_set_object(self.name))
