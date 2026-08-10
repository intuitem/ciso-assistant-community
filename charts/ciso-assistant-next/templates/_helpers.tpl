{{/*
Expand the name of the chart.
*/}}
{{- define "ciso-assistant.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ciso-assistant.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ciso-assistant.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Define CISO Assistant default tag version.
*/}}
{{- define "ciso-assistant.defaultTag" -}}
{{- default .Chart.AppVersion .Values.global.image.tag -}}
{{- end -}}

{{/*
Return valid version label
*/}}
{{- define "ciso-assistant.versionLabelValue" -}}
{{ regexReplaceAll "[^-A-Za-z0-9_.]" (include "ciso-assistant.defaultTag" .) "-" | trunc 63 | trimAll "-" | trimAll "_" | trimAll "." | quote }}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "ciso-assistant.labels" -}}
helm.sh/chart: {{ include "ciso-assistant.chart" .context }}
{{ include "ciso-assistant.selectorLabels" (dict "context" .context "component" .component) }}
app.kubernetes.io/managed-by: {{ .context.Release.Service }}
app.kubernetes.io/version: {{ include "ciso-assistant.versionLabelValue" .context }}
{{- with .context.Values.global.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ciso-assistant.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ciso-assistant.name" .context }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
{{- if .component }}
app.kubernetes.io/component: {{ .component }}
{{- end }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ciso-assistant.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ciso-assistant.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Define complete url based on scheme and domain
*/}}
{{- define "ciso-assistant.url" -}}
{{- $scheme := ternary "https" "http" (or .Values.global.tls .Values.ingress.tls.enabled) -}}
{{- printf "%s://%s" $scheme .Values.global.domain -}}
{{- end -}}

{{/*
Backend in-cluster API URL used by the frontend (includes the service port).
*/}}
{{- define "ciso-assistant.backendApiUrl" -}}
{{- printf "http://%s-backend:%v/api" (include "ciso-assistant.fullname" .) .Values.backend.service.port -}}
{{- end -}}

{{/*
Service name of the Qdrant subchart (mirrors its own "qdrant.fullname" template so
QDRANT_URL stays correct even when qdrant.nameOverride / fullnameOverride is set).
*/}}
{{- define "ciso-assistant.qdrantFullname" -}}
{{- if .Values.qdrant.fullnameOverride -}}
{{- .Values.qdrant.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default "qdrant" .Values.qdrant.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Qdrant in-cluster URL used by the backend for the AI / RAG feature.
Uses the Qdrant REST port (6333, fixed by the subchart's service).
*/}}
{{- define "ciso-assistant.qdrantUrl" -}}
{{- printf "http://%s:6333" (include "ciso-assistant.qdrantFullname" .) -}}
{{- end -}}

{{/*
Path of the merged CA bundle produced by the init container (system roots + extra CA).
*/}}
{{- define "ciso-assistant.extraCerts.bundlePath" -}}
{{- printf "%s/ca-bundle.crt" (trimSuffix "/" .Values.global.extraCerts.mountPath) -}}
{{- end -}}

{{/*
Extra CA env vars for Python containers (backend, Huey).
Points at the merged bundle so the system roots stay trusted (additive, not a replacement).
*/}}
{{- define "ciso-assistant.extraCerts.pythonEnv" -}}
{{- if .Values.global.extraCerts.enabled -}}
{{- $bundle := include "ciso-assistant.extraCerts.bundlePath" . -}}
- name: SSL_CERT_FILE
  value: {{ $bundle | quote }}
- name: REQUESTS_CA_BUNDLE
  value: {{ $bundle | quote }}
{{- end -}}
{{- end -}}

{{/*
Extra CA env var for Node containers (frontend).
NODE_EXTRA_CA_CERTS is additive to Node's built-in roots, so it points at the raw CA file.
*/}}
{{- define "ciso-assistant.extraCerts.nodeEnv" -}}
{{- if .Values.global.extraCerts.enabled -}}
- name: NODE_EXTRA_CA_CERTS
  value: {{ printf "%s/%s" (trimSuffix "/" .Values.global.extraCerts.mountPath) .Values.global.extraCerts.fileName | quote }}
{{- end -}}
{{- end -}}

{{/*
Init container that concatenates the system CA bundle with the extra CA into an emptyDir.
Expects a dict with "context", "image", "imagePullPolicy" and optional "securityContext".
*/}}
{{- define "ciso-assistant.extraCerts.initContainer" -}}
{{- $ctx := .context -}}
{{- if $ctx.Values.global.extraCerts.enabled -}}
{{- $bundle := include "ciso-assistant.extraCerts.bundlePath" $ctx -}}
- name: extra-certs-merge
  image: {{ .image }}
  imagePullPolicy: {{ .imagePullPolicy }}
  command: ["/bin/sh", "-c"]
  args:
    - set -e; cat /etc/ssl/certs/ca-certificates.crt "/tmp/extra-certs-src/{{ $ctx.Values.global.extraCerts.fileName }}" > {{ $bundle | quote }}
  volumeMounts:
    - name: extra-certs-src
      mountPath: /tmp/extra-certs-src
      readOnly: true
    - name: extra-certs
      mountPath: {{ $ctx.Values.global.extraCerts.mountPath }}
  {{- with .securityContext }}
  securityContext:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end -}}
{{- end -}}

{{/*
Volume mount for the merged bundle (read-only) used by the Python containers.
*/}}
{{- define "ciso-assistant.extraCerts.backendVolumeMount" -}}
{{- if .Values.global.extraCerts.enabled -}}
- name: extra-certs
  mountPath: {{ .Values.global.extraCerts.mountPath }}
  readOnly: true
{{- end -}}
{{- end -}}

{{/*
Backend pod volumes: the source secret (consumed by the init container) and the
emptyDir that holds the merged bundle.
*/}}
{{- define "ciso-assistant.extraCerts.backendVolumes" -}}
{{- if .Values.global.extraCerts.enabled -}}
- name: extra-certs-src
  secret:
    secretName: {{ required "global.extraCerts.secretName is required when global.extraCerts.enabled is true" .Values.global.extraCerts.secretName }}
    items:
      - key: {{ .Values.global.extraCerts.fileName }}
        path: {{ .Values.global.extraCerts.fileName }}
- name: extra-certs
  emptyDir: {}
{{- end -}}
{{- end -}}

{{/*
Frontend volume mount: the raw CA secret (NODE_EXTRA_CA_CERTS is additive, no merge needed).
*/}}
{{- define "ciso-assistant.extraCerts.frontendVolumeMount" -}}
{{- if .Values.global.extraCerts.enabled -}}
- name: extra-certs
  mountPath: {{ .Values.global.extraCerts.mountPath }}
  readOnly: true
{{- end -}}
{{- end -}}

{{/*
Frontend pod volume: the raw CA secret.
*/}}
{{- define "ciso-assistant.extraCerts.frontendVolume" -}}
{{- if .Values.global.extraCerts.enabled -}}
- name: extra-certs
  secret:
    secretName: {{ required "global.extraCerts.secretName is required when global.extraCerts.enabled is true" .Values.global.extraCerts.secretName }}
    items:
      - key: {{ .Values.global.extraCerts.fileName }}
        path: {{ .Values.global.extraCerts.fileName }}
{{- end -}}
{{- end -}}
