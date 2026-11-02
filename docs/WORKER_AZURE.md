# Ejecutar el diagnostico G7B en el laboratorio v3

Este paso sustituye la imagen smoke del Job existente por el worker de metadatos.
No es todavia el ETL de Parquet/DuckDB. No crea otro entorno, no cambia el lago,
no concede escritura a Blob y no programa ejecuciones automaticas.

## 1. Revisar desde Cloud Shell (Bash)

Usar un checkout limpio de la rama del PR #9; conservar backups fuera de esa carpeta.

```bash
cd "$HOME/g7b-cloud-shell"
git switch chatgpt/g7b-arquitectura-privada-ofertas-20261101
git pull --ff-only
bash infra/azure/activar_diagnostico.sh --revisar
```

Solo consulta suscripcion, storage, entorno, Job y registros ACR. Si no encuentra
el entorno WorkloadProfiles esperado o el Job manual, se detiene. No imprime
secretos ni descarga archivos del lago. El nombre historico del Job sigue siendo
`g7b-smoke-laboratorio`; tras aplicar, su imagen sera la del diagnostico G7B.

## 2. Registro privado y requisitos

Se requiere un ACR existente con permisos RBAC clasicos (no ABAC), tokens ARM
habilitados y conectividad desde Container Apps. El operador necesita construir
imagenes, actualizar el Job y asignar AcrPull. No habilitar usuario administrador.
La identidad del Job ya debe conservar Blob Data Reader sobre `lago`.

Si no existe ACR, elegir un nombre globalmente unico y revisar costo de Basic,
region, presupuesto y disponibilidad de ACR Tasks en la suscripcion estudiantil.
Solo despues de esa revision, crear el registro desde Cloud Shell:

```bash
export G7B_ACR='NOMBRE_UNICO_ELEGIDO'
REGION=$(az containerapp env show -g g7b -n g7b-env-laboratorio-jobs-v3 --query location -o tsv)
az acr create -g g7b -n "$G7B_ACR" --sku Basic --location "$REGION" --admin-enabled false --output none
```

Un registro privado autenticado no equivale a un endpoint aislado mediante Private
Link. Este paso no crea red privada. Si ACR Tasks no esta permitido, detenerse:
construir/publicar desde un entorno autorizado es una alternativa a evaluar, no
una razon para habilitar credenciales de administrador.

## 3. Publicar y configurar sin iniciar

Revisar el ID con `az account show --query '{nombre:name,id:id}' -o table`.
Establecer las confirmaciones solo cuando exista evidencia; no son comprobaciones
automaticas de presupuesto ni de revocacion SAS. No repetir una rotacion ya hecha.

```bash
export G7B_SUSCRIPCION='ID_VERIFICADO'
export G7B_ACR='NOMBRE_ACR_VERIFICADO'
export G7B_PRESUPUESTO_REVISADO=si
export G7B_ROTACION_CONFIRMADA=si
bash infra/azure/activar_diagnostico.sh --aplicar
```

El script envia a ACR solo Dockerfile y los modulos `g7b_ops/*.py`, etiqueta con
el commit y fija la imagen por digest. Concede AcrPull a la identidad de sistema
solo sobre ese registro. Sustituye las variables del contenedor por la URL sin SAS
y el nombre `lago`; establece `command=["python"]` y `args=["/opt/g7b/g7b_ops/auditoria.py"]`. No inicia el
Job. Guardar el digest y la imagen anterior que imprime el script. Si hay error,
los pasos anteriores pueden haberse aplicado: inspeccionar antes de repetir.

El SDK usa `ManagedIdentityCredential` para que esta prueba no pueda autenticarse
accidentalmente con credenciales de otro usuario. Docker conserva usuario sin root.

## 4. Ejecutar y acreditar el acceso

Tras la propagacion de RBAC:

```bash
bash infra/azure/activar_diagnostico.sh --ejecutar
```

Se inicia una ejecucion y se observa hasta 12 minutos. Un timeout de observacion
no cancela el trabajo. No iniciar otra sin comprobar la anterior. Para ver estado:

```bash
az containerapp job execution list -g g7b -n g7b-smoke-laboratorio \
  --query '[].{nombre:name,estado:properties.status,inicio:properties.startTime,fin:properties.endTime}' -o table
```

Para aceptar este hito deben coincidir: ejecucion `Succeeded`, imagen por digest
del worker y salida `G7B_AZURE_DIAGNOSTICO` de ESA ejecucion. El JSON incluye
conteos/tamanos por zona; cero objetos tambien puede ser una lectura valida.
No publica nombres individuales ni contenidos. Inspecciona como maximo 10000
objetos y marca `limite_alcanzado` si hay mas; no es un inventario exhaustivo.

Consultar las replicas y sus logs mientras esten disponibles (requiere extension
containerapp con soporte de logs):

```bash
export EJECUCION='NOMBRE_DEVUELTO_POR_EL_SCRIPT'
az containerapp job replica list -g g7b -n g7b-smoke-laboratorio --execution "$EJECUCION" -o table
export REPLICA='NOMBRE_DE_LA_REPLICA'
az containerapp job logs show -g g7b -n g7b-smoke-laboratorio \
  --execution "$EJECUCION" --replica "$REPLICA" --container smoke --tail 100
```

Si la replica termino y los logs ya no estan disponibles, falta evidencia de salida:
no inventarla. La retencion duradera requiere un destino de logs configurado y
presupuestado. Esta entrega no crea Log Analytics ni asegura dicha retencion.
No pegar logs completos sin revisar; conservar solo el marcador agregado y estado.

## Recuperacion y limites

Para volver a la imagen anterior, usar `az containerapp job update -g g7b -n
g7b-smoke-laboratorio --container-name smoke --image IMAGEN_ANTERIOR`. La
configuracion de registro y AcrPull permanecen; no retirar roles compartidos sin
revisar usos. No se revierte la creacion de ACR ni sus costos automaticamente.
No volver a desplegar la plantilla Bicep con la imagen smoke por defecto si se
quiere conservar este worker: suministrar `workerImage` con el digest aprobado.

La ejecucion real en Azure sigue pendiente hasta obtener la evidencia anterior.
Luego corresponde implementar y probar una transformacion pequena con permisos
de escritura acotados, salidas versionadas y calidad, antes de Geoda/Amatista.

Referencias oficiales consultadas para los comandos:
- [Registro del Job e identidad](https://learn.microsoft.com/en-us/cli/azure/containerapp/job/registry?view=azure-cli-latest)
- [Actualizar e iniciar Jobs](https://learn.microsoft.com/en-us/cli/azure/containerapp/job?view=azure-cli-latest)
- [Imagen privada con identidad administrada](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull)

## Si ACR Tasks no esta permitido

Ante `TasksOperationsNotAllowed`, usar [publicacion desde GitHub con OIDC](PUBLICAR_WORKER_OIDC.md). Esta alternativa conserva el ACR y permite configurar el Job con `G7B_IMAGEN_EXISTENTE`, sin volver a invocar ACR Tasks.

### Correccion del arranque

La ejecucion `g7b-smoke-laboratorio-z1vrdd8` termino Failed segun la salida del usuario. La plantilla mostraba command y args como `[""]`: esta version de CLI conservo cadenas vacias en lugar de retirar el override. Se corrige con comando y ruta Python explicitos. Esta evidencia identifica un defecto de configuracion; no sustituye los logs de causa final ni acredita acceso al lago. La nueva ejecucion debe verificarse por separado.
