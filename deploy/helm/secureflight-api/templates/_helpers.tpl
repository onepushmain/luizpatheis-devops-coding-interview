{{/* Chart name. */}}
{{- define "secureflight-api.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Fully qualified app name. */}}
{{- define "secureflight-api.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/* Selector labels (immutable once deployed). */}}
{{- define "secureflight-api.selectorLabels" -}}
app.kubernetes.io/name: {{ include "secureflight-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Common labels. */}}
{{- define "secureflight-api.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{ include "secureflight-api.selectorLabels" . }}
app.kubernetes.io/version: {{ .Values.image.tag | default .Chart.AppVersion | trunc 63 | quote }}
app.kubernetes.io/component: api
app.kubernetes.io/part-of: secureflight
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Container image reference. The tag (git SHA) is required and "latest" is
rejected. When a digest is set, the image is pulled by digest (immutable).
*/}}
{{- define "secureflight-api.image" -}}
{{- $tag := required "image.tag is required (git SHA)" .Values.image.tag -}}
{{- if eq $tag "latest" -}}
{{- fail "image.tag must be an immutable git SHA, not \"latest\"" -}}
{{- end -}}
{{- if .Values.image.digest -}}
{{- printf "%s@%s" .Values.image.repository .Values.image.digest -}}
{{- else -}}
{{- printf "%s:%s" .Values.image.repository $tag -}}
{{- end -}}
{{- end }}

{{/* ServiceAccount name. */}}
{{- define "secureflight-api.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "secureflight-api.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
