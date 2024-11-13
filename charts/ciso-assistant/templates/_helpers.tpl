{{/* Get the application version */}}
{{- define "ciso-assistant.appVersion" -}}
{{- default .Chart.AppVersion .Values.global.appVersion -}}
{{- end -}}
{{/* Common labels */}}
{{- define "common.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
