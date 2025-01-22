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
{{ include "ciso-assistant.selectorLabels" (dict "context" .context "component" .component "name" .name) }}
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
Define complete url based on scheme and domain
*/}}
{{- define "ciso-assistant.url" -}}
{{- $scheme := ternary "https" "http" .Values.global.tls -}}
{{- printf "%s://%s" $scheme .Values.global.domain -}}
{{- end -}}