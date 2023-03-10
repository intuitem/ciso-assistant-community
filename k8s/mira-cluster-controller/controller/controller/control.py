from kubernetes import client, config
import os

core_v1_api = None
apps_v1_api = None
try:
    config.load_incluster_config()
    print("inside cluster")
except:
    print("outside cluster")
    config.load_kube_config()

core_v1_api = client.CoreV1Api()
apps_v1_api = client.AppsV1Api()
networking_v1_api = client.NetworkingV1Api()

#https://blog.knoldus.com/how-to-create-statefulsets-workloads-using-kubernetes-python-client%EF%BF%BC/


def create_service(client_name):
    svc_name = f"mira-{client_name}"
    body = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(
            name=svc_name
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
    try:
        core_v1_api.create_namespaced_service(namespace="default", body=body)
    except client.exceptions.ApiException as e:
        if e.status == 409:
            print(f"Service {svc_name} already exists: replace it")
            core_v1_api.replace_namespaced_service(namespace="default", name=svc_name, body=body)
        else:
            print("Exception:", e)



def create_ingress(client_name, mira_domain):
    ingress_name = f"mira-{client_name}"
    svc_name = f"mira-{client_name}"
    body = client.V1Ingress(
        api_version="networking.k8s.io/v1",
        kind="Ingress",
        metadata=client.V1ObjectMeta(name=ingress_name, annotations={
            "nginx.ingress.kubernetes.io/backend-protocol": "HTTPS",
            "nginx.ingress.kubernetes.io/ssl-redirect": "true",
            "nginx.ingress.kubernetes.io/ssl-passthrough": "true"
        }),
        spec=client.V1IngressSpec(
            ingress_class_name="nginx",
            rules=[client.V1IngressRule(
                host=mira_domain,
                http=client.V1HTTPIngressRuleValue(
                    paths=[client.V1HTTPIngressPath(
                        path="/",
                        path_type="Prefix",
                        backend=client.V1IngressBackend(
                            service=client.V1IngressServiceBackend(
                                port=client.V1ServiceBackendPort(
                                    number=443,
                                ),
                                name=svc_name)
                            )
                    )]
                )
            )
            ]
        )
    )
    try:
        networking_v1_api.create_namespaced_ingress(namespace="default", body=body)
    except client.exceptions.ApiException as e:
        if e.status == 409:
            print(f"Ingress {svc_name} already exists: replace it")
            networking_v1_api.replace_namespaced_ingress(namespace="default", name=ingress_name, body=body)
        else:
            print("Exception:", e)



def create_stateful_set_object(client_name, email_admin, mira_url, sts_name):
    configmaps = [client.V1EnvFromSource(config_map_ref=client.V1ConfigMapEnvSource(name='mira-config'))]
    secret_smtp_out = client.V1EnvVarSource(secret_key_ref=client.V1SecretKeySelector(key="EMAIL_HOST_PASSWORD", name="smtp-out"))
    secret_recaptcha = client.V1EnvVarSource(secret_key_ref=client.V1SecretKeySelector(key="RECAPTCHA_PRIVATE_KEY", name="recaptcha"))
    mira_container = client.V1Container(
        name="mira",
        image="rg.fr-par.scw.cloud/funcscwmiraj3whjdnx/mira:latest",
        ports=[client.V1ContainerPort(container_port=8000)],
        env_from=configmaps,
        env=[client.V1EnvVar(name="MIRA_SUPERUSER_EMAIL", value=email_admin),
             client.V1EnvVar(name="EMAIL_HOST_PASSWORD", value_from=secret_smtp_out),
             client.V1EnvVar(name="RECAPTCHA_PRIVATE_KEY", value_from=secret_recaptcha),
             client.V1EnvVar(name="MIRA_URL", value=mira_url),
            ],
        volume_mounts=[client.V1VolumeMount(name="db-data", mount_path='/code/db')],
    )
    caddy_container = client.V1Container(
        name="caddy",
        image="caddy:latest",
        ports=[client.V1ContainerPort(container_port=80), client.V1ContainerPort(container_port=443)],
        volume_mounts=[client.V1VolumeMount(name="db-data", mount_path='/data', sub_path='caddy')],
        command=['caddy', 'reverse-proxy', '--from', mira_url, '--to', 'localhost:8000'],
    )
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={"app": "mira", "client": client_name}
        ),
        spec=client.V1PodSpec(
            enable_service_links=False,
            containers=[mira_container, caddy_container],
            volumes=[client.V1Volume(
                name='db-data',
                persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name='db-data'))
            ],
            image_pull_secrets=[client.V1LocalObjectReference(name="registry-secret")]
        ),
    )
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
    return client.V1StatefulSet(
        api_version="apps/v1",
        kind="StatefulSet",
        metadata=client.V1ObjectMeta(name=sts_name),
        spec=spec,
    )


def create_stateful_set(client_name, email_admin, mira_url):
        sts_name = f"mira-{client_name}"
        body=create_stateful_set_object(client_name, email_admin, mira_url, sts_name)
        try:
            apps_v1_api.create_namespaced_stateful_set(namespace="default", body=body)
        except client.exceptions.ApiException as e:
            if e.status == 409:
                print(f"StatefulSet {sts_name} already exists: replace it")
                apps_v1_api.replace_namespaced_stateful_set(namespace="default", name= sts_name, body=body)
            else:
                print("Exception:", e)


def create_client_objects(client_name, email_admin):
    cluster_domain = os.environ.get("CLUSTER_DOMAIN")
    if not cluster_domain:
        print("missing CLUSTER_DOMAIN environment variable - skipping creation of objects")
    else:
        mira_domain = f"{client_name}.{cluster_domain}"
        mira_url = f"https://{mira_domain}"
        create_service(client_name)
        create_ingress(client_name, mira_domain)
        create_stateful_set(client_name, email_admin, mira_url)

