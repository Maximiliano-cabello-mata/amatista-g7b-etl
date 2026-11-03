# G7B — Azure 24/7 con crédito estudiantil (Cloud Shell)

**Estado (2026-11-02):** laboratorio v3 y smoke manual completados según logs reportados por el usuario; no ejecutados ni consultados directamente en Azure durante esta revisión. [Bitácora](bitacoras/2026-11-02.md). Este runbook sirve para inspección y cambios posteriores; no requiere repetir el despliegue exitoso.

Entorno vigente: `g7b-env-laboratorio-jobs-v3`, API del entorno `2026-07-01`, `environmentMode: WorkloadProfiles`, perfil `Consumption`. Los intentos v1/v2 fallaron con `ExpressEnvironmentResourceNotSupported` y sus dos entornos Express fueron eliminados, según el usuario. No recrearlos.

## Qué significa 24/7

No mantener un proceso vivo dentro de Cloud Shell; su sesión es temporal.
El dato vive continuamente en Azure Blob Storage. El procesamiento funciona
a cualquier hora mediante Jobs programados, colas o eventos. Una API puede
escalar a cero para ahorrar, pero tendrá inicio frío; si se exige una respuesta
sin inicio frío y un uptime estricto se requiere capacidad activa, presupuesto
y evaluación de SLA. Un mismo plan de 100 USD no garantiza 12 meses de una VM.

## Crédito

Azure for Students ofrece habitualmente USD 100 por 12 meses y servicios
gratuitos limitados. El saldo restante y vencimiento están en
https://www.microsoftazuresponsorships.com/ o en Azure Education Hub.
El importe total del crédito no equivale al saldo disponible: investigar el
gasto real antes de dimensionar. Si se agota o caduca, se suspende Azure for
Students. Renovar es posible cuando la institución vuelve a verificar
elegibilidad. No habilitar pago por uso sin autorización expresa y plan.

El beneficio adicional de Visual Studio Dev Essentials es diferente y su
compatibilidad con la suscripción vigente debe confirmarse con Microsoft.
No sumar/promocionar cifras hasta que aparezcan explícitamente como
**saldo aplicado** en la suscripción que usa el lago.

Configurar un presupuesto con alertas y consultar costos al menos semanalmente.
Los presupuestos **no** apagan los servicios automáticamente y la evaluación de
gastos puede retrasarse varias horas. Reservar saldo para almacenamiento,
operaciones y recuperación antes de activar GPU o instancias dedicadas.

## Paso 1 — Solo lectura en Cloud Shell (Bash)

```bash
cd "$HOME"
git clone --depth 1 --branch chatgpt/g7b-arquitectura-privada-ofertas-20261101 \
  https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl.git g7b-cloud-shell
cd g7b-cloud-shell
bash infra/azure/diagnosticar_cloud_shell.sh
```

El script muestra nombre/estado de suscripción, recursos del grupo `g7b`,
configuración pública del almacenamiento, proveedores y presupuestos.
**No** lee ni imprime claves, tokens, cadenas de conexión ni archivos del lago.

Si la suscripción actual no es Azure for Students, elegir manualmente la
correcta usando `az account list -o table` y
`az account set --subscription "NOMBRE_EXACTO"`, y repetir el diagnóstico.

## Paso 2 — Incidente de SAS y continuidad de servicio

Estado de la revisión: el run `41381723814` devuelve 404; esto no prueba revocación SAS ni su eliminación. La remediación no está verificada aquí. Revisar evidencia existente antes de repetir acciones de rotación.

Según el reporte histórico, la cuenta de almacenamiento de G7B empleó la clave primaria para firmar una
SAS que fue visible en un registro público de GitHub Actions. Eliminar el log
sin revocar la SAS NO es suficiente.

**Antes de rotar:** identificar qué workflows de GitHub, Doppler, Zyte y otros
servicios están usando esa SAS. Planificar una ventana de actualización.

Con autorización, el procedimiento de revocación de esa SAS es regenerar la
clave primaria desde el portal o mediante:

```bash
# Reemplazar por NOMBRE DE CUENTA verificado, sin pegar valores secretos.
az storage account keys renew \
  --resource-group g7b --account-name NOMBRE_CUENTA \
  --key primary --output none
```

**Efecto:** otras SAS y clientes firmados con esa clave dejarán de funcionar.
Si la remediación sigue pendiente, actualizar dependencias y verificar operaciones básicas; revisar otros registros expuestos. El run `41381723814` ya no es accesible en la consulta realizada.
Nunca ejecutar `az storage account keys list` sin filtrar la salida:
imprime valores secretos. Preferir identidades administradas y OIDC.

## Paso 3 — Primero presupuesto y supervisión

En Portal Azure: **Cost Management + Billing → Budgets → Add** (en el alcance
de la suscripción o del grupo `g7b`). Configurar límite en la **moneda del
alcance**, alertas por consumo real (50%, 80%, 100%) y previsto, según
lo que permita la suscripción. Si hay USD 100 completos para 12 meses,
USD 8.33/mes es SOLO una referencia media, no el presupuesto recomendado
sin medir uso, ni un precio garantizado. Los avisos no son límite duro.

Configurar alertas para credenciales, errores y fallos de trabajos.
No levantar VMs, gateways, Private Link, GPU, Log Analytics premium o
instancias que cuesten todo el mes hasta medir tarifas y cuota.

## Paso 4 — Validar el diseño Azure (sin desplegar)

Solo tras rotación verificada:

```bash
cd "$HOME/g7b-cloud-shell"
export STORAGE_ACCOUNT_NAME="NOMBRE_CUENTA"
export G7B_ROTACION_CONFIRMADA=si
bash infra/azure/validar_y_aprovisionar.sh
```

El script compila Bicep y realiza un `what-if`. **No despliega** si no se
habilita explícitamente `G7B_APROVISIONAR=si` y
`G7B_PRESUPUESTO_REVISADO=si`. Antes de cambiar esos valores, revisar
roles, costos y el plan de regiones. La plantilla actual solo crea un
`smoke` manual, no ejecuta G7B continuamente.

## Qué sigue

1. Verificar evidencia de presupuesto, cuotas y monitoreo; no confirmados en esta revisión.
2. Verificar evidencia de revocación SAS y acceso efectivo al lago mediante identidad administrada; no inferirlos del 404 o del smoke.
3. Crear registro de contenedores privado, publicar worker real de G7B, y
   configurar permisos de lectura y escritura por separado.
4. Programar extracción y transformación con retención y calidad.
5. Implementar API/console privada, control de identidades, publicación
   versionada hacia Geoda y mecanismo de rollback.
6. Evaluar SLA, recuperación ante desastres y presupuesto recurrente.

La iniciativa puede dar cobertura continua de datos sin dejar el procesador
ocupado de manera continua. Todo lo demás requiere evidencia operativa real.

## Inspección del laboratorio existente (solo lectura)

Estos comandos son de consulta; no se ejecutaron durante la actualización documental:

```bash
az resource list -g g7b --query "[].{nombre:name,tipo:type}" -o table
az containerapp env show -g g7b -n g7b-env-laboratorio-jobs-v3 \
  --query "{estado:properties.provisioningState,modo:properties.environmentMode,perfiles:properties.workloadProfiles}" -o json
az containerapp job show -g g7b -n g7b-smoke-laboratorio \
  --query "{estado:properties.provisioningState,entorno:properties.environmentId,trigger:properties.configuration.triggerType}" -o json
az containerapp job execution list -g g7b -n g7b-smoke-laboratorio \
  --query "[].{nombre:name,estado:properties.status,inicio:properties.startTime,fin:properties.endTime}" -o table
```

Referencia histórica: `g7b-smoke-laboratorio-ex51o9l`, `Succeeded`, 2026-11-02 06:09:43–06:10:40 UTC (57 s). Inventario reportado: storage `g7blago09b52a0e`, entorno v3 y Job. Si la ejecución ya no aparece, conservar la distinción entre historial reportado y estado consultado. No deducir acceso al lago, ETL real, presupuesto ni revocación SAS de estas consultas.

## Siguiente paso: worker de diagnostico

El procedimiento para publicar la imagen privada, configurar el Job existente y comprobar lectura mediante identidad administrada esta en [WORKER_AZURE.md](WORKER_AZURE.md). Su preparacion y pruebas simuladas no acreditan una ejecucion real en Azure.
