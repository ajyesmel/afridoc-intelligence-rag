#!/usr/bin/env bash
set -euo pipefail
# Prerequisites: az login; Azure CLI containerapp extension; active subscription.
: "${AZURE_RESOURCE_GROUP:?Specify AZURE_RESOURCE_GROUP}"
: "${AZURE_LOCATION:=southafricanorth}"
: "${AZURE_APP_NAME:=afridoc-api}"
: "${APP_API_KEY:?Specify APP_API_KEY}"
: "${DATABASE_URL:?Specify managed PostgreSQL DATABASE_URL}"
[[ "$DATABASE_URL" == postgresql* ]] || { echo "Cloud requires PostgreSQL (no ephemeral SQLite)." >&2; exit 1; }
az extension add --name containerapp --upgrade >/dev/null
az provider register --namespace Microsoft.App >/dev/null
az containerapp up --name "$AZURE_APP_NAME" --resource-group "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" --source . --ingress external --target-port 8000
az containerapp secret set --name "$AZURE_APP_NAME" --resource-group "$AZURE_RESOURCE_GROUP" \
  --secrets "app-key=$APP_API_KEY" "db-url=$DATABASE_URL" >/dev/null
az containerapp update --name "$AZURE_APP_NAME" --resource-group "$AZURE_RESOURCE_GROUP" \
  --set-env-vars "APP_API_KEY=secretref:app-key" "DATABASE_URL=secretref:db-url" >/dev/null
if [[ -n "${GROQ_API_KEY:-}" ]]; then
  az containerapp secret set --name "$AZURE_APP_NAME" --resource-group "$AZURE_RESOURCE_GROUP" \
    --secrets "groq-key=$GROQ_API_KEY" >/dev/null
  az containerapp update --name "$AZURE_APP_NAME" --resource-group "$AZURE_RESOURCE_GROUP" \
    --set-env-vars "GROQ_API_KEY=secretref:groq-key" >/dev/null
fi
az containerapp show --name "$AZURE_APP_NAME" --resource-group "$AZURE_RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv
