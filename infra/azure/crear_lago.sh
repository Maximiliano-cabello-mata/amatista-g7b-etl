#!/usr/bin/env bash
# Crea el lago de datos de G7B en Azure. Se corre en Azure Cloud Shell (Bash),
# que ya trae la CLI de Azure y la sesión iniciada: portal.azure.com › icono >_ .
#
#   bash crear_lago.sh                       # usa los valores por omisión
#   UBICACION=southcentralus bash crear_lago.sh
#
# Se puede correr más de una vez: lo que ya existe se deja como está.
# Al final imprime AZURE_LAGO_URL. Cópiala a Doppler y a los secretos de
# GitHub. No la pegues en ningún chat ni la subas a Git.
set -euo pipefail
trap 'echo "ERROR: el script se detuvo en la línea $LINENO. Copia el mensaje de arriba (sin llaves) para revisarlo." >&2' ERR

GRUPO="${GRUPO:-g7b}"
UBICACION="${UBICACION:-mexicocentral}"
CONTENEDOR="lago"
AQUI="$(cd "$(dirname "$0")" && pwd)"

echo "== Suscripción activa"
az account show --query "{nombre:name, id:id}" -o table

if [ -z "${CUENTA:-}" ]; then
  # Reusar la cuenta del grupo si ya existe; si no, crear un nombre nuevo (único en todo Azure).
  CUENTA="$(az storage account list -g "$GRUPO" --query "[?tags.proyecto=='g7b'].name | [0]" -o tsv 2>/dev/null || true)"
  if [ -z "$CUENTA" ]; then
    # Sin tuberías: con pipefail, "tr ... | head" termina el script en silencio.
    CUENTA="g7blago$(printf '%04x%04x' "$RANDOM" "$RANDOM")"
  fi
fi
echo "== Cuenta de almacenamiento: $CUENTA (grupo $GRUPO, región $UBICACION)"

echo "== Servicio de almacenamiento registrado en la suscripción (las nuevas no lo traen)"
if [ "$(az provider show -n Microsoft.Storage --query registrationState -o tsv 2>/dev/null)" != "Registered" ]; then
  az provider register --namespace Microsoft.Storage --wait -o none
fi

echo "== Grupo de recursos"
az group create -n "$GRUPO" -l "$UBICACION" --tags proyecto=g7b -o none

echo "== Cuenta de almacenamiento (LRS, privada, solo HTTPS, TLS 1.2)"
if ! az storage account show -n "$CUENTA" -g "$GRUPO" -o none 2>/dev/null; then
  az storage account create -n "$CUENTA" -g "$GRUPO" -l "$UBICACION" \
    --sku Standard_LRS --kind StorageV2 --access-tier Hot \
    --allow-blob-public-access false --min-tls-version TLS1_2 --https-only true \
    --tags proyecto=g7b capa=lago -o none
fi

echo "== Papelera de 7 días para archivos y contenedores borrados"
az storage account blob-service-properties update -n "$CUENTA" -g "$GRUPO" \
  --enable-delete-retention true --delete-retention-days 7 \
  --enable-container-delete-retention true --container-delete-retention-days 7 -o none

CLAVE="$(az storage account keys list -n "$CUENTA" -g "$GRUPO" --query '[0].value' -o tsv)"

echo "== Contenedor '$CONTENEDOR' (sin acceso público)"
az storage container create -n "$CONTENEDOR" --account-name "$CUENTA" --account-key "$CLAVE" \
  --public-access off -o none

echo "== Ciclo de vida: bronce pasa a Cool a los 30 días; tmp se borra a los 7"
az storage account management-policy create --account-name "$CUENTA" -g "$GRUPO" \
  --policy @"$AQUI/politica_ciclo.json" -o none

echo "== Firma de acceso (SAS) del contenedor: leer, agregar, crear, escribir y listar; sin borrar; vence en 1 año"
EXPIRA="$(date -u -d '+1 year' '+%Y-%m-%dT%H:%MZ')"
SAS="$(az storage container generate-sas -n "$CONTENEDOR" --account-name "$CUENTA" --account-key "$CLAVE" \
  --permissions racwl --expiry "$EXPIRA" --https-only -o tsv)"

echo
echo "Listo. Guarda este valor como secreto AZURE_LAGO_URL (Doppler y GitHub). Vence el $EXPIRA."
echo
echo "AZURE_LAGO_URL=https://${CUENTA}.blob.core.windows.net/${CONTENEDOR}?${SAS}"
echo
echo "Siguiente: crear el presupuesto con avisos en el portal (infra/azure/LEEME.md, paso 4)."
