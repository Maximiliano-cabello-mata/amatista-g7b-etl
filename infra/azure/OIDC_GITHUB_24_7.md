# G7B sin SAS caducables: identidad federada Azure / GitHub Actions

**Objetivo:** que Zyte → Bronce → Plata → MongoDB y el Cubo → Geoda puedan seguir ejecutándose sin renovar manualmente la SAS de 24 h. El código admite OIDC, pero **requiere configurar una identidad y permisos en Azure y variables en GitHub**; la instalación no se realiza automáticamente al fusionar este cambio.

## Por qué

El 4 de noviembre de 2026, el run [41757705929](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41757705929) falló por `AuthenticationFailed`: la SAS expiró a las 01:01 UTC y el job leyó Azure a las 01:59 UTC. El problema es la credencial; no se ha detectado corrupción del cubo anterior.

El SDK ahora prioriza `AZURE_STORAGE_ACCOUNT_URL` con `DefaultAzureCredential`, que usa la sesión de Azure CLI de `azure/login@v2`. Si no se configuró, conserva `AZURE_LAGO_URL` (SAS legado) y `AZURE_STORAGE_CONNECTION_STRING` (Azurite).

## Configurar una vez, desde Azure Cloud Shell

Requisitos: cuenta con permisos para **registrar una aplicación** en Microsoft Entra y **crear asignaciones de rol** sobre el contenedor. Si no tienes estos permisos, no inventes credenciales: solicita a un administrador que configure la federación.

```bash
set -euo pipefail
az account set --subscription "Azure for Students"
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
STORAGE_ID="$(az storage account show -g g7b -n g7blago09b52a0e --query id -o tsv)"
SCOPE="$STORAGE_ID/blobServices/default/containers/lago"

APP_ID="$(az ad app create --display-name g7b-github-actions-oidc --query appId -o tsv)"
SP_ID="$(az ad sp create --id "$APP_ID" --query id -o tsv)"

cat > /tmp/g7b-github-federacion.json <<'JSON'
{
  "name": "github-amatista1",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:Maximiliano-cabello-mata/amatista-g7b-etl:environment:amatista1",
  "audiences": ["api://AzureADTokenExchange"],
  "description": "Acceso temporal a Azure Blob desde GitHub Actions sin client secret"
}
JSON

az ad app federated-credential create --id "$APP_ID" --parameters /tmp/g7b-github-federacion.json
az role assignment create \
  --assignee-object-id "$SP_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "$SCOPE"
```

**Importante:** este rol autoriza escribir datos en el contenedor `lago`. No conceder `Owner` al workflow. Verificar los permisos con la identidad federada en una prueba controlada antes de habilitar tareas continuas.

## Registrar variables no secretas en GitHub

Desde una Cloud Shell con `gh auth login` completado, en la misma sesión de las variables anteriores:

```bash
REPO=Maximiliano-cabello-mata/amatista-g7b-etl
gh variable set AZURE_CLIENT_ID -b "$APP_ID" -R "$REPO"
gh variable set AZURE_TENANT_ID -b "$TENANT_ID" -R "$REPO"
gh variable set AZURE_SUBSCRIPTION_ID -b "$SUBSCRIPTION_ID" -R "$REPO"
gh variable set AZURE_STORAGE_ACCOUNT_URL -b "https://g7blago09b52a0e.blob.core.windows.net" -R "$REPO"
```

No hace falta ningún `AZURE_CLIENT_SECRET`. Mantén `MONGO_URI` y `ZYTE_API_KEY` en los secretos del environment `amatista1`, sin mostrarlos en logs.

Los workflows `vigilar`, `zyte_a_lago`, `procesar`, `telemetria`, `cubo` y `geoda_publicar` ahora obtienen permisos de token OIDC con `id-token: write` y ejecutan `azure/login@v2` cuando las variables federadas están configuradas.

## Verificar antes de activar las tareas programadas

```bash
REPO=Maximiliano-cabello-mata/amatista-g7b-etl
gh workflow run cubo.yml -R "$REPO" --ref main
gh run list -R "$REPO" --workflow cubo.yml --limit 3
```

Consultar logs sin imprimir credenciales: se debe ver la construcción del cubo, verificación SHA-256 y descarga del puntero vigente, sin `AuthenticationFailed`.

Después ejecutar manualmente `geoda_publicar.yml`. Comprobar que `publicacion/geoda.json` esté en `main`, contenga solo conteos, y la API pública de Amatista reporte `estado=conectado` tras desplegar ambos repositorios.

**Solo después** activar las variables de repositorio:

```bash
gh variable set G7B_INGESTA_ACTIVA -b true -R "$REPO"
gh variable set G7B_GEODA_PUBLICAR_ACTIVA -b true -R "$REPO"
```

No debes activar dos cadenas de extracción que operen sobre los mismos trabajos sin verificar idempotencia y cuota de Zyte. Controla los costos, la licencia de datos y alertas de fallo.

## Qué significa 24/7

Los servicios gestionados (Azure Blob, MongoDB, Zyte) y la VM API de Amatista pueden estar disponibles permanentemente; GitHub Actions **no es un proceso residente** y las tareas programadas pueden retrasarse. La automatización trabajará por cron/eventos sin necesidad de Cloud Shell. Configura avisos de fallos, límites de consumo y comprobaciones externas de `/api/salud`.

Para apagar las tareas programadas: establecer `G7B_INGESTA_ACTIVA=false` y `G7B_GEODA_PUBLICAR_ACTIVA=false`. Las ejecuciones manuales aún se pueden iniciar si es necesario. Tras verificar varios ciclos OIDC, se podrá retirar la SAS antigua del environment sin afectar a los workflows actualizados.
