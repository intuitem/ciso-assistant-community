from kubernetes import client, config

core_v1_api = None
apps_v1_api = None
try:
    config.load_incluster_config()
except:
    print("not in cluster")
    config.load_kube_config()

core_v1_api = client.CoreV1Api()
apps_v1_api = client.AppsV1Api()


#https://blog.knoldus.com/how-to-create-statefulsets-workloads-using-kubernetes-python-client%EF%BF%BC/


def create_service(core_v1_api, client_name):
    body = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(
            name=f"svc-mira-{client_name}"
        ),
        spec=client.V1ServiceSpec(
            selector={f"client": client_name},
            type="ClusterIP",
            ports=[
                client.V1ServicePort(port=80,target_port=80, name="http"),
                client.V1ServicePort(port=443,target_port=443, name="https"),
            ]
        )
    )
    core_v1_api.create_namespaced_service(namespace="default", body=body)


def create_stateful_set_object(client_name, email_admin):
    configmaps = [
        client.V1EnvFromSource(config_map_ref=client.V1ConfigMapEnvSource(name='mira-config')),
    ]
    secret = client.V1EnvVarSource(secret_key_ref=client.V1SecretKeySelector(key="EMAIL_HOST_PASSWORD", name="myvars"))
    mira_container = client.V1Container(
        name="mira",
        image="rg.fr-par.scw.cloud/funcscwmiraj3whjdnx/mira:latest",
        ports=[client.V1ContainerPort(container_port=8000)],
        env_from=configmaps,
        env=[client.V1EnvVar(name="MIRA_SUPERUSER_EMAIL", value=email_admin),
             client.V1EnvVar(name="EMAIL_HOST_PASSWORD", value_from=secret),
            ],
        volume_mounts=[client.V1VolumeMount(name="db-data", mount_path='/code/db')],
    )
    mira_domain = client.V1EnvVarSource(config_map_key_ref=client.V1ConfigMapKeySelector(key="MIRA_DOMAIN", name="mira-config"))
    caddy_container = client.V1Container(
        name="caddy",
        image="caddy:latest",
        ports=[client.V1ContainerPort(container_port=80), client.V1ContainerPort(container_port=443)],
        env=[client.V1EnvVar(name="MIRA_DOMAIN", value_from=mira_domain)],
        volume_mounts=[client.V1VolumeMount(name="db-data", mount_path='/data', sub_path='caddy')],
        command=['caddy', 'reverse-proxy', '--from', '$(MIRA_DOMAIN)', '--to', 'localhost:8000'],
    )
    # Template
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={"app": "mira", "client": client_name}
        ),
        spec=client.V1PodSpec(
            containers=[mira_container, caddy_container],
            volumes=[client.V1Volume(
                name='db-data',
                persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name='db-data'))
            ],
            image_pull_secrets=[client.V1LocalObjectReference(name="registry-secret")]
        ),
    )
    # Spec

    volume_claim = client.V1PersistentVolumeClaim(
        api_version='v1',
        kind='PersistentVolumeClaim',
        metadata=client.V1ObjectMeta(
            name='db-data',
            labels={"app": "mira"},
        ),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=['ReadWriteOnce'],
            resources=client.V1ResourceRequirements(requests={'storage': '1Gi'})
        )
    )
    spec = client.V1StatefulSetSpec(
        replicas=1,
        service_name=f"svc-mira-{client_name}",
        selector=client.V1LabelSelector(match_labels={"app": "mira"}),
        template=template,
        volume_claim_templates=[volume_claim],
)
    # StatefulSet
    statefulset = client.V1StatefulSet(
        api_version="apps/v1",
        kind="StatefulSet",
        metadata=client.V1ObjectMeta(name=f"sts-mira-{client_name}"),
        spec=spec,
    )

    return statefulset


def create_stateful_set(apps_v1_api, stateful_set_object):
    # Create the Statefulset in default namespace
    # You can replace the namespace with you have created
    apps_v1_api.create_namespaced_stateful_set(
        namespace="default", body=stateful_set_object
    )

def main():
#    print(apps_v1_api.list_namespaced_stateful_set("default"))
#    create_service(core_v1_api, "toto")
    stateful_set_obj = create_stateful_set_object("toto", "root@example.com")
    create_stateful_set(apps_v1_api, stateful_set_obj)

if __name__ == "__main__":
    main()

