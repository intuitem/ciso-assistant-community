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
Qdrant in-cluster URL used by the backend for the AI / RAG feature.
*/}}
{{- define "ciso-assistant.qdrantUrl" -}}
{{- printf "http://%s-qdrant:%v" (include "ciso-assistant.fullname" .) .Values.qdrant.service.port -}}
{{- end -}}

{{/*
Extra CA certificate env vars (wires both the Python and Node trust stores).
*/}}
{{- define "ciso-assistant.extraCerts.env" -}}
{{- if .Values.global.extraCerts.enabled -}}
{{- $certFile := printf "%s/%s" (trimSuffix "/" .Values.global.extraCerts.mountPath) .Values.global.extraCerts.fileName -}}
- name: SSL_CERT_FILE
  value: {{ $certFile | quote }}
- name: REQUESTS_CA_BUNDLE
  value: {{ $certFile | quote }}
- name: NODE_EXTRA_CA_CERTS
  value: {{ $certFile | quote }}
{{- end -}}
{{- end -}}

{{/*
Extra CA certificate volume mount.
*/}}
{{- define "ciso-assistant.extraCerts.volumeMount" -}}
{{- if .Values.global.extraCerts.enabled -}}
- name: extra-certs
  mountPath: {{ .Values.global.extraCerts.mountPath }}
  readOnly: true
{{- end -}}
{{- end -}}

{{/*
Extra CA certificate volume (sourced from an existing secret).
*/}}
{{- define "ciso-assistant.extraCerts.volume" -}}
{{- if .Values.global.extraCerts.enabled -}}
- name: extra-certs
  secret:
    secretName: {{ required "global.extraCerts.secretName is required when global.extraCerts.enabled is true" .Values.global.extraCerts.secretName }}
    items:
      - key: {{ .Values.global.extraCerts.fileName }}
        path: {{ .Values.global.extraCerts.fileName }}
{{- end -}}
{{- end -}}
