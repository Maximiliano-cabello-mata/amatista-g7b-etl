#!/usr/bin/env bash
# Configura confianza GitHub -> Azure solo para la rama del PR #9.
set -euo pipefail
[[ "${1:-}" == --aplicar ]] || { echo 'Uso: bash infra/azure/configurar_publicacion_oidc.sh --aplicar'; exit 2; }
REPO=Maximiliano-cabello-mata/amatista-g7b-etl
RAMA=chatgpt/g7b-arquitectura-privada-ofertas-20261101
# Subject exacto observado en el run 41407548404; GitHub incluye IDs inmutables.
SUJETO="repo:Maximiliano-cabello-mata@335839614/amatista-g7b-etl@1441384047:ref:refs/heads/$RAMA"
IDENTIDAD=g7b-github-acr
ACR=g7bacr09b52a0e
command -v gh >/dev/null
gh auth status >/dev/null
: "${G7B_SUSCRIPCION:?Usa el ID de la suscripcion revisada}"
ACTUAL=$(az account show --query id -o tsv)
[[ "$ACTUAL" == "$G7B_SUSCRIPCION" ]] || { echo 'Suscripcion distinta de la prevista' >&2; exit 2; }
ACR_ID=$(az acr show -g g7b -n "$ACR" --query id -o tsv)
[[ -n "$ACR_ID" ]] || exit 2
MODO=$(az acr show -g g7b -n "$ACR" --query roleAssignmentMode -o tsv)
[[ "$MODO" == LegacyRegistryPermissions ]] || { echo 'Se requiere RBAC clasico' >&2; exit 2; }
# Desactivar publicacion hasta completar toda la configuracion.
gh variable set G7B_ACR_OIDC_LISTO --repo "$REPO" --body no
az provider register --namespace Microsoft.ManagedIdentity --wait --output none
az identity create -g g7b -n "$IDENTIDAD" -l westus2 --output none
CLIENTE=$(az identity show -g g7b -n "$IDENTIDAD" --query clientId -o tsv)
PRINCIPAL=$(az identity show -g g7b -n "$IDENTIDAD" --query principalId -o tsv)
TENANT=$(az identity show -g g7b -n "$IDENTIDAD" --query tenantId -o tsv)
az identity federated-credential create -g g7b --identity-name "$IDENTIDAD" --name github-pr9 --issuer https://token.actions.githubusercontent.com --subject "$SUJETO" --audiences api://AzureADTokenExchange --output none
az role assignment create --assignee-object-id "$PRINCIPAL" --assignee-principal-type ServicePrincipal --role AcrPush --scope "$ACR_ID" --output none
# Azure CLI necesita leer la configuracion ARM del registro para az acr login.
az role assignment create --assignee-object-id "$PRINCIPAL" --assignee-principal-type ServicePrincipal --role Reader --scope "$ACR_ID" --output none
gh variable set G7B_AZURE_CLIENT_ID --repo "$REPO" --body "$CLIENTE"
gh variable set G7B_AZURE_TENANT_ID --repo "$REPO" --body "$TENANT"
gh variable set G7B_AZURE_SUBSCRIPTION_ID --repo "$REPO" --body "$ACTUAL"
gh variable set G7B_ACR_OIDC_LISTO --repo "$REPO" --body si
echo 'OIDC_CONFIGURADO: identidad con AcrPush y Reader solo sobre el ACR; no se inicio el Job.'
echo 'Tras propagacion de permisos, publicar con un commit que contenga [publicar-worker].'
