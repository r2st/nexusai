{{/*
Expand the name of the chart.
*/}}
{{- define "nexusai.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "nexusai.fullname" -}}
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

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "nexusai.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "nexusai.labels" -}}
helm.sh/chart: {{ include "nexusai.chart" . }}
{{ include "nexusai.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "nexusai.selectorLabels" -}}
app.kubernetes.io/name: {{ include "nexusai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Backend labels
*/}}
{{- define "nexusai.backend.labels" -}}
{{ include "nexusai.labels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{- define "nexusai.backend.selectorLabels" -}}
{{ include "nexusai.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Frontend labels
*/}}
{{- define "nexusai.frontend.labels" -}}
{{ include "nexusai.labels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{- define "nexusai.frontend.selectorLabels" -}}
{{ include "nexusai.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Worker labels
*/}}
{{- define "nexusai.worker.labels" -}}
{{ include "nexusai.labels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{- define "nexusai.worker.selectorLabels" -}}
{{ include "nexusai.selectorLabels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "nexusai.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "nexusai.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Database host
*/}}
{{- define "nexusai.databaseHost" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "nexusai.fullname" .) }}
{{- else }}
{{- .Values.externalDatabase.host }}
{{- end }}
{{- end }}

{{/*
Database port
*/}}
{{- define "nexusai.databasePort" -}}
{{- if .Values.postgresql.enabled }}
{{- 5432 }}
{{- else }}
{{- .Values.externalDatabase.port }}
{{- end }}
{{- end }}

{{/*
Database URL
*/}}
{{- define "nexusai.databaseUrl" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "postgresql+asyncpg://%s:$(DATABASE_PASSWORD)@%s:%d/%s" .Values.postgresql.auth.username (include "nexusai.databaseHost" .) (include "nexusai.databasePort" . | int) .Values.postgresql.auth.database }}
{{- else }}
{{- printf "postgresql+asyncpg://%s:$(DATABASE_PASSWORD)@%s:%d/%s" .Values.externalDatabase.username (include "nexusai.databaseHost" .) (include "nexusai.databasePort" . | int) .Values.externalDatabase.database }}
{{- end }}
{{- end }}

{{/*
Redis host
*/}}
{{- define "nexusai.redisHost" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" (include "nexusai.fullname" .) }}
{{- else }}
{{- .Values.externalRedis.host }}
{{- end }}
{{- end }}

{{/*
Redis port
*/}}
{{- define "nexusai.redisPort" -}}
{{- if .Values.redis.enabled }}
{{- 6379 }}
{{- else }}
{{- .Values.externalRedis.port }}
{{- end }}
{{- end }}

{{/*
Redis URL
*/}}
{{- define "nexusai.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- printf "redis://:%s@%s:%d/0" "$(REDIS_PASSWORD)" (include "nexusai.redisHost" .) (include "nexusai.redisPort" . | int) }}
{{- else }}
{{- printf "redis://:%s@%s:%d/0" "$(REDIS_PASSWORD)" (include "nexusai.redisHost" .) (include "nexusai.redisPort" . | int) }}
{{- end }}
{{- end }}

{{/*
Meilisearch host
*/}}
{{- define "nexusai.meilisearchHost" -}}
{{- if .Values.meilisearch.enabled }}
{{- printf "http://%s-meilisearch:7700" (include "nexusai.fullname" .) }}
{{- else }}
{{- "" }}
{{- end }}
{{- end }}

{{/*
Image pull secrets
*/}}
{{- define "nexusai.imagePullSecrets" -}}
{{- with .Values.global.imagePullSecrets }}
imagePullSecrets:
{{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}
