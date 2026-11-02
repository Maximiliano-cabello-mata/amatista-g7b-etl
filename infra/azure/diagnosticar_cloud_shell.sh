#!/usr/bin/env bash
# DIAGNOSTICO PARA CLOUD SHELL (Bash): cero recursos creados, cero llaves leidas.
# Solo imprime nombres de recursos, suscripcion, presupuestos y seguridad publica.
# No se leen contenidos de Blob ni claves de acceso.
set -euo pipefail
export AZURE_CORE_ONLY_SHOW_ERRORS=true
RG="$(printenv G7B_GRUPO || true)"
RG="$(echo "$RG" | tr -d '[:space:]')"
if [ -z "$RG" ]; then RG="g7b"; fi

if ! command -v az >/dev/null 2>&1; then
  echo "ERROR: necesita Azure CLI en Cloud Shell (Bash)." >&2
  exit 2
fi
printf '\n== G7B | SUSCRIPCIONES DISPONIBLES ==\n'
az account list --query "[].{Nombre:name,Estado:state,Actual:isDefault}" -o table
printf '\n== G7B | SUSCRIPCION SELECCIONADA ==\n'
az account show --query "{Nombre:name,Estado:state}" -o table
TIPO="$(az account show --query name -o tsv)"
if [[ "$TIPO" != *"Students"* && "$TIPO" != *"Estudiantes"* ]]; then
  echo "AVISO: esta suscripcion no identifica claramente Azure for Students."
  echo "Revisa la seleccion antes de aprovisionar."
fi

printf '\n== G7B | GRUPO DE RECURSOS ==\n'
if [[ "$(az group exists -n "$RG")" != "true" ]]; then
  echo "No existe el grupo $RG en la suscripcion activa. Sin cambios."
  exit 0
fi
az group show -n "$RG" --query "{Nombre:name,Region:location,Estado:properties.provisioningState}" -o table

printf '\n== G7B | INVENTARIO DE RECURSOS ==\n'
az resource list -g "$RG" --query "[].{Nombre:name,Tipo:type,Region:location}" -o table

printf '\n== G7B | ALMACENAMIENTO (NO SE LEEN CLAVES NI SAS) ==\n'
az storage account list -g "$RG" \
  --query "[].{Cuenta:name,Region:location,Sku:sku.name,Publico:allowBlobPublicAccess,HTTPS:enableHttpsTrafficOnly,TLS:minimumTlsVersion}" \
  -o table

printf '\n== G7B | REGISTRO DE SERVICIOS (SOLO LECTURA) ==\n'
for provider in Microsoft.Storage Microsoft.App Microsoft.ContainerRegistry Microsoft.OperationalInsights Microsoft.CostManagement; do
  estado="$(az provider show -n "$provider" --query registrationState -o tsv 2>/dev/null || echo 'no disponible')"
  printf '%-38s %s\n' "$provider" "$estado"
done

printf '\n== G7B | PRESUPUESTOS EXISTENTES ==\n'
if az consumption budget list -g "$RG" \
  --query "[].{Nombre:name,Cantidad:amount,Periodo:timeGrain}" -o table; then
  echo "Se completo la consulta. Un presupuesto no corta automaticamente el gasto."
else
  echo "No disponible: puede faltar permiso o todavia no estar habilitada esta funcion."
fi

printf '\n== G7B | RESULTADO ==\n'
echo "G7B_DIAGNOSTICO_CLOUD_SHELL_COMPLETADO"
echo "No se han creado recursos, cambiado claves, leido SAS ni habilitado facturacion."
echo "Consulta saldo restante y caducidad en Azure Sponsorships / Education Hub."
