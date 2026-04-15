{{- define "openwebui-leaderboard.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "openwebui-leaderboard.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "openwebui-leaderboard.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "openwebui-leaderboard.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" -}}
{{- end -}}

{{- define "openwebui-leaderboard.labels" -}}
helm.sh/chart: {{ include "openwebui-leaderboard.chart" . }}
app.kubernetes.io/name: {{ include "openwebui-leaderboard.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "openwebui-leaderboard.selectorLabels" -}}
app.kubernetes.io/name: {{ include "openwebui-leaderboard.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "openwebui-leaderboard.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "openwebui-leaderboard.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "openwebui-leaderboard.databaseUrl" -}}
{{- if .Values.database.url -}}
{{- .Values.database.url -}}
{{- else if eq .Values.database.type "sqlite" -}}
{{- printf "sqlite:///%s" .Values.database.sqlite.path -}}
{{- else -}}
{{- printf "postgresql://%s:%s@%s:%v/%s?sslmode=%s" .Values.database.postgresql.username .Values.database.postgresql.password .Values.database.postgresql.host .Values.database.postgresql.port .Values.database.postgresql.database .Values.database.postgresql.sslmode -}}
{{- end -}}
{{- end -}}
