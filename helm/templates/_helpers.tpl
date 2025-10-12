{{- define "somafractalmemory.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "somafractalmemory.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "somafractalmemory.selectorLabels" -}}
app.kubernetes.io/name: {{ include "somafractalmemory.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/part-of: {{ .Chart.Name }}
{{- end -}}

{{- define "somafractalmemory.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{ include "somafractalmemory.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
{{- end -}}

{{- define "somafractalmemory.podAnnotations" -}}
{{- $annotations := dict -}}
{{- with .Values.podAnnotations }}
	{{- $annotations = merge $annotations . -}}
{{- end }}
{{- if .Values.secret.rolloutRestart.enabled }}
	{{- if .Values.secret.rolloutRestart.annotations }}
		{{- $annotations = merge $annotations .Values.secret.rolloutRestart.annotations -}}
	{{- else }}
		{{- $annotations = merge $annotations (dict "reloader.stakater.com/auto" "true") -}}
	{{- end }}
{{- end }}
{{- if gt (len $annotations) 0 }}
{{ toYaml $annotations }}
{{- end -}}
{{- end -}}

{{- define "somafractalmemory.secretName" -}}
{{- if .Values.secret.existingSecret }}
{{ .Values.secret.existingSecret }}
{{- else -}}
{{- $defaultName := printf "%s-secrets" (include "somafractalmemory.fullname" .) -}}
{{- default $defaultName .Values.secret.name -}}
{{- end -}}
{{- end -}}
