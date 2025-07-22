# ciso-assistant

![Version: 0.4.4](https://img.shields.io/badge/Version-0.4.4-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: v2.7.7](https://img.shields.io/badge/AppVersion-v2.7.7-informational?style=flat-square)

A Helm chart for CISO Assistant k8s's deployment

**Homepage:** <https://intuitem.com>

## Source Code

* <https://github.com/intuitem/ciso-assistant-community>

## Requirements

| Repository | Name | Version |
|------------|------|---------|
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

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| backend.annotations | object | `{}` | Backend deployment annotations |
| backend.config.databaseType | string | `"sqlite"` | Set the database type (sqlite, pgsql or externalPgsql) # Note : PostgreSQL database configuration at `postgresql` or `externalPgsql` section |
| backend.config.djangoDebug | bool | `false` | Enable Django debug mode |
| backend.config.djangoExistingSecretKey | string | `""` | Name of an existing secret resource containing the django secret in a 'django-secret-key' key |
| backend.config.djangoSecretKey | string | `"changeme"` | Set Django secret key |
| backend.config.emailAdmin | string | `"admin@example.net"` | Admin email for initial configuration |
| backend.config.smtp.defaultFrom | string | `"no-reply@ciso-assistant.net"` | Default from email address |
| backend.config.smtp.existingSecret | string | `""` | Name of an existing secret resource containing the SMTP password in a 'email-primary-password' key |
| backend.config.smtp.host | string | `"smtp.server.local"` | SMTP hostname |
| backend.config.smtp.password | string | `""` | SMTP password |
| backend.config.smtp.port | int | `25` | SMTP post |
| backend.config.smtp.useTls | bool | `false` | Enable TLS for SMTP |
| backend.config.smtp.username | string | `""` | SMTP username |
| backend.containerSecurityContext | object | `{}` | Toggle and define container-level security context |
| backend.env | list | `[]` | Environment variables to pass to backend |
| backend.huey.env | list | `[]` | Environment variables to pass to Huey |
| backend.huey.name | string | `"huey"` | Huey container name |
| backend.huey.resources | object | `{}` | Resources for Huey |
| backend.image.imagePullPolicy | string | `""` (defaults to global.image.imagePullPolicy) | Image pull policy for the backend |
| backend.image.registry | string | `""` (defaults to global.image.registry) | Registry to use for the backend |
| backend.image.repository | string | `"intuitem/ciso-assistant-community/backend"` | Repository to use for the backend |
| backend.image.tag | string | `""` (defaults to global.image.tag) | Tag to use for the backend |
| backend.imagePullSecrets | list | `[]` (defaults to global.imagePullSecrets) | Secrets with credentials to pull images from a private registry |
| backend.name | string | `"backend"` | Backend container name |
| backend.persistence.localStorage.accessMode | string | `"ReadWriteOnce"` | Local Storage persistant volume accessMode |
| backend.persistence.localStorage.enabled | bool | `false` | Enable Local Storage persistence |
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
| externalPgsql.database | string | `"ciso-assistant"` | Database inside an external PostgreSQL to connect |
| externalPgsql.existingSecret | string | `""` | Secret containing the password of an external PostgreSQL instance to connect # Name of an existing secret resource containing the DB password in a 'password' key |
| externalPgsql.host | string | `""` | Host of an external PostgreSQL instance to connect |
| externalPgsql.password | string | `""` | Password of an external PostgreSQL instance to connect |
| externalPgsql.port | int | `5432` | Port of an external PostgreSQL to connect |
| externalPgsql.user | string | `"ciso-assistant"` | User of an external PostgreSQL instance to connect |
| frontend.annotations | object | `{}` | Frontend deployment annotations |
| frontend.config.bodySizeLimit | string | `"50M"` | Configure body size limit for uploads in bytes (unit suffix like K/M/G can be used) |
| frontend.containerSecurityContext | object | `{}` | Toggle and define container-level security context |
| frontend.env | list | `[]` | Environment variables to pass to frontend |
| frontend.image.imagePullPolicy | string | `""` (defaults to global.image.imagePullPolicy) | Image pull policy for the frontend |
| frontend.image.registry | string | `""` (defaults to global.image.registry) | Registry to use for the frontend |
| frontend.image.repository | string | `"intuitem/ciso-assistant-community/frontend"` | Repository to use for the frontend |
| frontend.image.tag | string | `""` (defaults to global.image.tag) | Tag to use for the frontend |
| frontend.imagePullSecrets | list | `[]` (defaults to global.imagePullSecrets) | Secrets with credentials to pull images from a private registry |
| frontend.name | string | `"frontend"` | Frontend container name |
| frontend.podAnnotations | object | `{}` | Frontend pod annotations |
| frontend.replicas | int | `1` | The number of frontend pods to run |
| frontend.resources | object | `{}` | Resources for the frontend |
| frontend.service.annotations | object | `{}` | Frontend service annotations |
| frontend.service.labels | object | `{}` | Frontend service labels |
| frontend.service.port | int | `80` | Frontend service http port |
| frontend.service.portName | string | `"http"` | Frontend service port name |
| fullnameOverride | string | `""` | String to fully override `"ciso-assistant.fullname"` |
| global.clusterDomain | string | `"cluster.local"` | Kubernetes cluster domain name |
| global.commonLabels | object | `{}` | Labels to add to all deployed objects |
| global.domain | string | `"octopus.foo.bar"` | Default domain used by all components # Used for ingresses, certificates, environnement vars, etc. |
| global.extraAllowedHosts | string | `""` | Extra allowed hosts (comma separated, without spaces) |
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
| postgresql.enabled | bool | `false` | Enable to deploy PostgreSQL. |
| postgresql.global.postgresql.auth.database | string | `"ciso-assistant"` | Database name |
| postgresql.global.postgresql.auth.password | string | `""` | Database user account password # Note: if not set, it will be dynamically generated |
| postgresql.global.postgresql.auth.postgresPassword | string | `""` | Super-user postgres account password # Note: if not set, it will be dynamically generated |
| postgresql.global.postgresql.auth.username | string | `"ciso-assistant"` | Database username |
| postgresql.primary.persistence.size | string | `"5Gi"` | PostgreSQL persistant volume size (default 8Gi). |

----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.14.2](https://github.com/norwoodj/helm-docs/releases/v1.14.2)
