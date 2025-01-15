# ciso-assistant



![Version: 0.1.0](https://img.shields.io/badge/Version-0.1.0-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: v2.0.6](https://img.shields.io/badge/AppVersion-v2.0.6-informational?style=flat-square) 

A Helm chart for CISO Assistant k8s's deployment

**Homepage:** <https://intuitem.com>



## Source Code

* <https://github.com/intuitem/ciso-assistant-community>

## Requirements

| Repository | Name | Version |
|------------|------|---------|
| oci://registry-1.docker.io/bitnamicharts | postgresql | 16.4.2 |

## Installing the chart

To install the chart, firt get the values.yaml file and customize values.

```
helm show values oci://ghcr.io/intuitem/ciso-assistant > custom.yaml
```
To deploy the release :
```
helm install ciso-assistant-release oci://ghcr.io/intuitem/ciso-assistant -f custom.yaml
```

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| backend.config.databaseType | string | `"sqlite"` | Set the database type (sqlite, pgsql or externalPgsql) # Note : PostgreSQL database configuration at `postgresql` or `externalPgsql` section |
| backend.config.djangoDebug | bool | `false` | Enable Django debug mode |
| backend.config.djangoSecretKey | string | `"changeme"` | Set Django secret key |
| backend.config.emailAdmin | string | `"admin@example.net"` | Admin email for initial configuration |
| backend.config.smtp.defaultFrom | string | `"no-reply@ciso-assistant.net"` | Default from email address |
| backend.config.smtp.primary.host | string | `"primary.cool-mailer.net"` | Primary SMTP hostname |
| backend.config.smtp.primary.password | string | `"primary_password_here"` | Primary SMTP password |
| backend.config.smtp.primary.port | int | `587` | Primary SMTP post |
| backend.config.smtp.primary.useTls | bool | `true` | Enable TLS for primary SMTP |
| backend.config.smtp.primary.username | string | `"apikey"` | Primary SMTP username |
| backend.config.smtp.rescue.host | string | `"smtp.secondary.mailer.cloud"` | Rescue SMTP hostname |
| backend.config.smtp.rescue.password | string | `"rescue_password_here"` | Rescue SMTP hostname |
| backend.config.smtp.rescue.port | int | `587` | Rescue SMTP hostname |
| backend.config.smtp.rescue.useTls | bool | `true` | Enable TLS for rescue SMTP |
| backend.config.smtp.rescue.username | string | `"username"` | Rescue SMTP hostname |
| backend.containerSecurityContext | object | `{}`  | Toggle and define container-level security context |
| backend.env | list | `[]` | Environment variables to pass to backend |
| backend.image.imagePullPolicy | string | `""` (defaults to global.image.imagePullPolicy) | Image pull policy for the backend |
| backend.image.registry | string | `""` (defaults to global.image.registry) | Registry to use for the backend |
| backend.image.repository | string | `"intuitem/ciso-assistant-community/backend"` | Repository to use for the backend |
| backend.image.tag | string | `""` (defaults to global.image.tag) | Tag to use for the backend |
| backend.imagePullSecrets | list | `[]` (defaults to global.imagePullSecrets) | Secrets with credentials to pull images from a private registry |
| backend.name | string | `"backend"` | Backend name |
| backend.persistence.localStorage.accessMode | string | `"ReadWriteOnce"` | Local Storage persistant volume accessMode |
| backend.persistence.localStorage.enabled | bool | `true` | Enable Local Storage persistence |
| backend.persistence.localStorage.size | string | `"5Gi"` | Local Storage persistant volume size |
| backend.persistence.localStorage.storageClass | string | `""` | Local Storage persistant volume storageClass |
| backend.persistence.sqlite.accessMode | string | `"ReadWriteOnce"` | SQLite persistant volume accessMode |
| backend.persistence.sqlite.enabled | bool | `true` | Enable SQLite persistence Note: only when `backend.config.databaseType` use `sqlite` value |
| backend.persistence.sqlite.size | string | `"5Gi"` | SQLite persistant volume size |
| backend.persistence.sqlite.storageClass | string | `""` | SQLite persistant volume storageClass |
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
| frontend.config.bodySizeLimit | string | `"50M"` | Configure body size limit for uploads in bytes (unit suffix like K/M/G can be used) |
| frontend.containerSecurityContext | object | `{}`  | Toggle and define container-level security context |
| frontend.env | list | `[]` | Environment variables to pass to frontend |
| frontend.image.imagePullPolicy | string | `""` (defaults to global.image.imagePullPolicy) | Image pull policy for the frontend |
| frontend.image.registry | string | `""` (defaults to global.image.registry) | Registry to use for the frontend |
| frontend.image.repository | string | `"intuitem/ciso-assistant-community/frontend"` | Repository to use for the frontend |
| frontend.image.tag | string | `""` (defaults to global.image.tag) | Tag to use for the frontend |
| frontend.imagePullSecrets | list | `[]` (defaults to global.imagePullSecrets) | Secrets with credentials to pull images from a private registry |
| frontend.name | string | `"frontend"` | Frontend name |
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
| global.image.imagePullPolicy | string | `"IfNotPresent"` | If defined, a imagePullPolicy applied to all CISO Assistant deployments |
| global.image.registry | string | `"ghcr.io"` | If defined, a registry applied to all CISO Assistant deployments |
| global.image.tag | string | `""` | Overrides the global CISO Assistant image tag whose default is the chart appVersion |
| global.imagePullSecrets | list | `[]` | Secrets with credentials to pull images from a private registry |
| global.nodeSelector | object | `{}` | Default node selector for all components |
| global.securityContext | object | `{}`  | Toggle and define pod-level security context |
| global.tls | bool | `false` | Globally enable TLS (Ingress, URLs, etc.) |
| global.tolerations | list | `[]` | Default tolerations for all components |
| ingress.annotations | object | `{}` | Additional ingress annotations |
| ingress.certificateSecret | object | `{}` | Custom TLS certificate as secret # Note: 'key' and 'certificate' are expected in PEM format |
| ingress.enabled | bool | `true` | Enable an ingress resource for the CISO Assistant |
| ingress.ingressClassName | string | `""` | Defines which ingress controller will implement the resource |
| ingress.labels | object | `{}` | Additional ingress labels |
| ingress.path | string | `"/"` | The path to CISO Assistant |
| ingress.pathType | string | `"Prefix"` | Ingress path type. One of `Exact`, `Prefix` or `ImplementationSpecific` |
| nameOverride | string | `"ciso-assistant"` | Provide a name in place of `ciso-assistant` |
| postgresql.enabled | bool | `false` | Enable to deploy PostgreSQL. |
| postgresql.global.postgresql.auth.database | string | `"ciso-assistant"` | Database name |
| postgresql.global.postgresql.auth.password | string | `""` | Database user account password # Note: if not set, it will be dynamically generated |
| postgresql.global.postgresql.auth.postgresPassword | string | `""` | Super-user postgres account password # Note: if not set, it will be dynamically generated |
| postgresql.global.postgresql.auth.username | string | `"ciso-assistant"` | Database username |
| postgresql.primary.persistence.size | string | `"5Gi"` | PostgreSQL persistant volume size (default 8Gi). |


----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.14.2](https://github.com/norwoodj/helm-docs/releases/v1.14.2)