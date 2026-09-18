# ciso-assistant

![Version: 0.13.0](https://img.shields.io/badge/Version-0.13.0-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: v4.0.4](https://img.shields.io/badge/AppVersion-v4.0.4-informational?style=flat-square)

A Helm chart for CISO Assistant k8s's deployment

**Homepage:** <https://intuitem.com>

## Source Code

* <https://github.com/intuitem/ciso-assistant-community>

## Development

Update schema command after new updates on `values.yaml` (using https://github.com/losisin/helm-values-schema-json) :
```bash
helm schema --values values.yaml
```

Update `README.md` with helm-docs (using https://github.com/norwoodj/helm-docs) :
```bash
helm-docs
```

## Requirements

| Repository | Name | Version |
|------------|------|---------|
| https://qdrant.github.io/qdrant-helm | qdrant | 1.18.2 |
| oci://registry-1.docker.io/bitnamicharts | postgresql | 16.6.3 |

## Installing the chart

To install the chart, firt get the values.yaml file and customize values.

```
helm show values oci://ghcr.io/intuitem/helm-charts/ce/ciso-assistant > custom.yaml
```

Make sure to pin the appVersion to one of the official releases, if you don't want the app to auto-update each time you restart the deployment.

To deploy the release :
```
helm install ciso-assistant-release oci://ghcr.io/intuitem/helm-charts/ce/ciso-assistant -f custom.yaml
```

## Customizing the deployment

Everything below is driven from `values.yaml`, no chart patching needed.

### Container command and args

`backend`, `backend.huey` and `frontend` each accept `command` and `args`. Left empty, the image
entrypoint is used. The Huey worker carries its command in the values, so the number of workers or
the scheduler interval can be changed without editing the chart :

```yaml
backend:
  huey:
    args: ["-c", "python manage.py run_huey -w 4 --scheduler-interval 30"]
```

### Qdrant (AI assistant / RAG)

The `qdrant` section is passed through to the [official Qdrant chart](https://github.com/qdrant/qdrant-helm).
Its image and pull secrets are its own, `global.image.*` and `global.imagePullSecrets` do not apply :

```yaml
qdrant:
  enabled: true
  image:
    repository: registry.example.com/mirror/qdrant
    tag: v1.18.2
  imagePullSecrets:
    - name: my-registry-creds
```

Any other key from the Qdrant chart values (`nodeSelector`, `securityContext`, `service`, `ingress`, ...)
can be set under `qdrant` and is kept across `helm upgrade`.

### OIDC signing key (service accounts)

The backend signs the tokens issued to service accounts with an RSA key. The chart generates one on
first install, stores it in the `<release>-backend-oidc` secret and injects it as
`IDP_OIDC_PRIVATE_KEY` into the backend and Huey containers. Without it each container writes its own
key to `IDP_OIDC_PRIVATE_KEY_FILE` inside its own filesystem, so the key changes on every restart and
differs between replicas.

To bring your own key :

```yaml
backend:
  config:
    oidcProvider:
      # secret holding the PEM in an 'idp-oidc-private-key' entry
      existingSecret: my-oidc-signing-key
```

Switching to an `existingSecret` deletes the chart-managed one, so coming back later issues a new
key rather than the previous one.

Changing `privateKey` rolls the backend pods on its own, and so does switching to or from an
`existingSecret`. Rotating the content of an `existingSecret` in place does not, the pods have to be
restarted by hand (same as `djangoExistingSecretKey` and the SMTP one). When manifests are rendered
without cluster access (`helm template`, GitOps tooling), the chart cannot read the generated key back
and issues a new one on each render : set `existingSecret` or `privateKey` in that case.

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| backend.affinity | object | `{}` | Affinity rules for backend |
| backend.annotations | object | `{}` | Backend deployment annotations |
| backend.args | list | `[]` (image arguments) | Override the backend container arguments |
| backend.command | list | `[]` (image entrypoint) | Override the backend container entrypoint |
| backend.config.chat.enabled | bool | `false` | Enable the AI assistant / chat feature (sets ENABLE_CHAT) |
| backend.config.databaseType | string | `"sqlite"` | Set the database type (sqlite, pgsql or externalPgsql) # Note: PostgreSQL database configuration at `postgresql` or `externalPgsql` section |
| backend.config.djangoDebug | bool | `false` | Enable Django debug mode |
| backend.config.djangoExistingSecretKey | string | `""` | Name of an existing secret resource containing the django secret in a 'django-secret-key' key |
| backend.config.djangoSecretKey | string | `"changeme"` | Set Django secret key |
| backend.config.emailAdmin | string | `"admin@example.net"` | Admin email for initial configuration |
| backend.config.oidcProvider.existingSecret | string | `""` | Name of an existing secret resource containing the RSA private key in a 'idp-oidc-private-key' key |
| backend.config.oidcProvider.privateKey | string | `""` (generated once, then kept in the `<release>-backend-oidc` secret) | RSA private key (PEM) signing the OIDC tokens |
| backend.config.smtp.defaultFrom | string | `"no-reply@ciso-assistant.net"` | Default from email address |
| backend.config.smtp.existingSecret | string | `""` | Name of an existing secret resource containing the SMTP password in a 'email-primary-password' key |
| backend.config.smtp.host | string | `"smtp.server.local"` | SMTP hostname |
| backend.config.smtp.password | string | `""` | SMTP password |
| backend.config.smtp.port | int | `25` | SMTP post |
| backend.config.smtp.useSsl | bool | `false` | Enable SSL for SMTP (implicit TLS) # Note: useSsl takes precedence over useTls when both are enabled |
| backend.config.smtp.useTls | bool | `false` | Enable TLS for SMTP (explicit TLS) |
| backend.config.smtp.username | string | `""` | SMTP username |
| backend.containerSecurityContext | object | `{}` | Toggle and define container-level security context |
| backend.env | list | `[]` | Environment variables to pass to backend |
| backend.extraVolumeMounts | list | `[]` | Set extra volume mounts for backend container |
| backend.extraVolumes | list | `[]` | Set extra volumes for backend |
| backend.huey.args | list | `["-c","python manage.py run_huey -w 2 --scheduler-interval 60"]` | Override the Huey container arguments |
| backend.huey.command | list | `["/bin/sh"]` | Override the Huey container entrypoint |
| backend.huey.env | list | `[]` | Environment variables to pass to Huey |
| backend.huey.extraVolumeMounts | list | `[]` | Set extra volume mounts for Huey container |
| backend.huey.name | string | `"huey"` | Huey container name |
| backend.huey.resources | object | `{}` | Resources for Huey |
| backend.image.imagePullPolicy | string | `""` (defaults to global.image.imagePullPolicy) | Image pull policy for the backend |
| backend.image.registry | string | `""` (defaults to global.image.registry) | Registry to use for the backend |
| backend.image.repository | string | `"intuitem/ciso-assistant-community/backend"` | Repository to use for the backend |
| backend.image.tag | string | `""` (defaults to global.image.tag) | Tag to use for the backend |
| backend.imagePullSecrets | list | `[]` (defaults to global.imagePullSecrets) | Secrets with credentials to pull images from a private registry |
| backend.name | string | `"backend"` | Backend container name |
| backend.nodeSelector | object | `{}` | Default node selector for backend |
| backend.persistence.localStorage.accessMode | string | `"ReadWriteOnce"` | Local Storage persistant volume accessMode |
| backend.persistence.localStorage.enabled | bool | `false` | Enable Local Storage persistence # Note: required for file uploads (evidences, attachments, chat documents). # Disabled, each container falls back to its own ephemeral path and the backend # and Huey containers no longer see the same files. |
| backend.persistence.localStorage.existingClaim | string | `""` | Name of an existing PersistentVolumeClaim for local storage. Must be different from sqlite PVC |
| backend.persistence.localStorage.size | string | `"5Gi"` | Local Storage persistant volume size |
| backend.persistence.localStorage.storageClass | string | `""` | Local Storage persistant volume storageClass |
| backend.persistence.sqlite.accessMode | string | `"ReadWriteOnce"` | SQLite persistant volume accessMode |
| backend.persistence.sqlite.enabled | bool | `false` | Enable SQLite persistence (for backend and/or Huey) # Note: Needed for Huey, also when `backend.config.databaseType` is not set to `sqlite` |
| backend.persistence.sqlite.existingClaim | string | `""` | Name of an existing PersistentVolumeClaim for sqlite |
| backend.persistence.sqlite.size | string | `"5Gi"` | SQLite persistant volume size |
| backend.persistence.sqlite.storageClass | string | `""` | SQLite persistant volume storageClass |
| backend.podAnnotations | object | `{}` | Backend pod annotations |
| backend.replicas | int | `1` | The number of backend pods to run |
| backend.resources | object | `{}` | Resources for the backend |
| backend.service.annotations | object | `{}` | Backend service annotations |
| backend.service.labels | object | `{}` | Backend service labels |
| backend.service.port | int | `80` | Backend service http port |
| backend.service.portName | string | `"http"` | Backend service port name |
| backend.tolerations | list | `[]` | Default tolerations for backend |
| externalPgsql.database | string | `"ciso-assistant"` | Database inside an external PostgreSQL to connect |
| externalPgsql.existingSecret | string | `""` | Secret containing the password of an external PostgreSQL instance to connect # Name of an existing secret resource containing the DB password in a 'password' key |
| externalPgsql.host | string | `""` | Host of an external PostgreSQL instance to connect |
| externalPgsql.password | string | `""` | Password of an external PostgreSQL instance to connect |
| externalPgsql.port | int | `5432` | Port of an external PostgreSQL to connect |
| externalPgsql.user | string | `"ciso-assistant"` | User of an external PostgreSQL instance to connect |
| frontend.affinity | object | `{}` | Affinity rules for frontend |
| frontend.annotations | object | `{}` | Frontend deployment annotations |
| frontend.args | list | `[]` (image arguments) | Override the frontend container arguments |
| frontend.command | list | `[]` (image entrypoint) | Override the frontend container entrypoint |
| frontend.config.bodySizeLimit | string | `"50M"` | Configure body size limit for uploads in bytes (unit suffix like K/M/G can be used) |
| frontend.containerSecurityContext | object | `{}` | Toggle and define container-level security context |
| frontend.env | list | `[]` | Environment variables to pass to frontend |
| frontend.extraVolumeMounts | list | `[]` | Set extra volume mounts for frontend container |
| frontend.extraVolumes | list | `[]` | Set extra volumes for frontend |
| frontend.image.imagePullPolicy | string | `""` (defaults to global.image.imagePullPolicy) | Image pull policy for the frontend |
| frontend.image.registry | string | `""` (defaults to global.image.registry) | Registry to use for the frontend |
| frontend.image.repository | string | `"intuitem/ciso-assistant-community/frontend"` | Repository to use for the frontend |
| frontend.image.tag | string | `""` (defaults to global.image.tag) | Tag to use for the frontend |
| frontend.imagePullSecrets | list | `[]` (defaults to global.imagePullSecrets) | Secrets with credentials to pull images from a private registry |
| frontend.name | string | `"frontend"` | Frontend container name |
| frontend.nodeSelector | object | `{}` | Default node selector for frontend |
| frontend.podAnnotations | object | `{}` | Frontend pod annotations |
| frontend.replicas | int | `1` | The number of frontend pods to run |
| frontend.resources | object | `{}` | Resources for the frontend |
| frontend.service.annotations | object | `{}` | Frontend service annotations |
| frontend.service.labels | object | `{}` | Frontend service labels |
| frontend.service.port | int | `80` | Frontend service http port |
| frontend.service.portName | string | `"http"` | Frontend service port name |
| frontend.tolerations | list | `[]` | Default tolerations for frontend |
| fullnameOverride | string | `""` | String to fully override `"ciso-assistant.fullname"` |
| global.affinity | object | `{}` | Affinity rules for all components |
| global.clusterDomain | string | `"cluster.local"` | Kubernetes cluster domain name |
| global.commonLabels | object | `{}` | Labels to add to all deployed objects |
| global.domain | string | `"octopus.foo.bar"` | Default domain used by all components # Used for ingresses, certificates, environnement vars, etc. |
| global.extraAllowedHosts | string | `""` | Extra allowed hosts (comma separated, without spaces) |
| global.extraCerts.enabled | bool | `false` | Trust an extra CA certificate on all pods (added to the default roots, not replacing them) |
| global.extraCerts.fileName | string | `"ca.crt"` | Key inside the secret (also the file name once mounted) |
| global.extraCerts.mountPath | string | `"/etc/ssl/extra-certs"` | Directory where the certificate / merged bundle is mounted |
| global.extraCerts.secretName | string | `""` | Name of an existing secret holding the CA certificate |
| global.image.imagePullPolicy | string | `"IfNotPresent"` | If defined, a imagePullPolicy applied to all CISO Assistant deployments |
| global.image.registry | string | `"ghcr.io"` | If defined, a registry applied to all CISO Assistant deployments |
| global.image.tag | string | `""` | Overrides the global CISO Assistant image tag whose default is the chart appVersion |
| global.imagePullSecrets | list | `[]` | Secrets with credentials to pull images from a private registry |
| global.nodeSelector | object | `{}` | Default node selector for all components |
| global.securityContext | object | `{}` | Toggle and define pod-level security context |
| global.tls | bool | `false` | Globally enable TLS (URLs, etc.) |
| global.tolerations | list | `[]` | Default tolerations for all components |
| ingress.annotations | object | `{}` | Additional ingress annotations |
| ingress.enabled | bool | `false` | Enable an ingress resource for the CISO Assistant |
| ingress.ingressClassName | string | `""` | Defines which ingress controller will implement the resource |
| ingress.labels | object | `{}` | Additional ingress labels |
| ingress.path | string | `"/"` | The path to CISO Assistant |
| ingress.pathType | string | `"Prefix"` | Ingress path type. One of `Exact`, `Prefix` or `ImplementationSpecific` |
| ingress.tls.certificateSecret | object | `{}` | Custom TLS certificate as secret # Note: 'key' and 'certificate' are expected in PEM format |
| ingress.tls.enabled | bool | `false` | Enable TLS for the ingress |
| ingress.tls.existingSecret | string | `""` | Use existing TLS secret |
| nameOverride | string | `"ciso-assistant"` | Provide a name in place of `ciso-assistant` |
| networkPolicy.egress | list | `[]` | Egress rules (raw Kubernetes NetworkPolicy `egress` entries) |
| networkPolicy.enabled | bool | `false` | Create a NetworkPolicy for CISO Assistant pods |
| networkPolicy.ingress | list | `[]` | Ingress rules (raw Kubernetes NetworkPolicy `ingress` entries) |
| networkPolicy.podSelector | object | all pods of this release | Pod selector the policy applies to |
| networkPolicy.policyTypes | list | `["Ingress"]` | Policy types to enable (Ingress and/or Egress) |
| postgresql.enabled | bool | `false` | Enable to deploy PostgreSQL. |
| postgresql.global.postgresql.auth.database | string | `"ciso-assistant"` | Database name |
| postgresql.global.postgresql.auth.password | string | `""` | Database user account password # Note: if not set, it will be dynamically generated |
| postgresql.global.postgresql.auth.postgresPassword | string | `""` | Super-user postgres account password # Note: if not set, it will be dynamically generated |
| postgresql.global.postgresql.auth.username | string | `"ciso-assistant"` | Database username |
| postgresql.primary.persistence.size | string | `"5Gi"` | PostgreSQL persistant volume size (default 8Gi). |
| qdrant.config | object | `{"cluster":{"consensus":{"tick_period_ms":100},"enabled":true,"p2p":{"enable_tls":false,"port":6335}},"service":{"enable_tls":false}}` | Qdrant runtime configuration |
| qdrant.enabled | bool | `false` | Deploy the bundled Qdrant (official subchart) and inject QDRANT_URL |
| qdrant.env | list | `[]` | Environment variables to pass to Qdrant |
| qdrant.image.pullPolicy | string | `"IfNotPresent"` | Image pull policy for Qdrant |
| qdrant.image.repository | string | `"docker.io/qdrant/qdrant"` | Qdrant image repository, registry included (point it at your own mirror if needed) |
| qdrant.image.tag | string | `""` (defaults to the Qdrant subchart appVersion) | Tag to use for Qdrant |
| qdrant.imagePullSecrets | list | `[]` | Secrets with credentials to pull the Qdrant image from a private registry # Note: the Qdrant subchart has its own pull secrets, `global.imagePullSecrets` does not apply |
| qdrant.persistence | object | `{"accessModes":["ReadWriteOnce"],"additionalLabels":{},"annotations":{},"size":"10Gi"}` | Qdrant storage persistence |
| qdrant.replicaCount | int | `1` | Number of Qdrant replicas (requires `qdrant.config.cluster.enabled`) |
| qdrant.resources | object | `{}` | Resources for Qdrant |
| serviceAccount.annotations | object | `{}` | Annotations applied to created service account |
| serviceAccount.automountServiceAccountToken | bool | `true` | Automount API credentials for the Service Account |
| serviceAccount.create | bool | `false` | Create a service account for CISO Assistant |
| serviceAccount.labels | object | `{}` | Labels applied to created service account |
| serviceAccount.name | string | `""` (defaults to fullname) | Service account name |

----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.14.2](https://github.com/norwoodj/helm-docs/releases/v1.14.2)
