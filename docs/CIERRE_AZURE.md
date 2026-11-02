# Cierre operativo de Azure G7B

## Estado y siguiente accion

Azure ejecuta el auditor privado y ya se comprobo la entrega persistida de su
marcador: una fila de la ejecucion a665997 a las 16:49:00.3267357 UTC, tabla
ContainerAppConsoleLogs_CL. Ya no se investiga una averia de logs no demostrada.
Falta completar reconciliacion, migracion planificada, alertas y recuperacion.
La evidencia de Azure procede de las salidas del usuario del 2026-11-02;
las comprobaciones de CI no acceden a la suscripcion.

Desde Cloud Shell Bash, una sola revision sin modificar Azure:

```bash
cd "$HOME/g7b-cloud-shell" &&
git switch chatgpt/g7b-arquitectura-privada-ofertas-20261101 &&
git pull --ff-only &&
bash infra/azure/consolidar_azure.sh --plan
```

Si la carpeta no existe en una sesion efimera, recuperar el checkout:

```bash
git clone --branch chatgpt/g7b-arquitectura-privada-ofertas-20261101 \
  https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl.git "$HOME/g7b-cloud-shell"
```

El script comprueba region, perfil, imagen, comando, recursos, registro, identidad,
federacion OIDC y roles requeridos en sus alcances exactos. Conserva las etiquetas
del Job en el plan. Una diferencia detiene la preparacion: no la corrige a ciegas.
No inicia Jobs ni cambia recursos. `--plan` usa what-if y requiere Bicep disponible
en Azure CLI. No hay modo aplicar. El reporte de cambios muestra rutas de
propiedades, no valores que pudieran contener secretos.

La nueva plantilla `g7b-operacion.bicep` representa el Job con la imagen real.
Entorno, lago, ACR, identidad de publicacion y workspace son dependencias existentes:
no se crean ni se reconfiguran con esa plantilla. Sus roles se comprueban; no se
duplican asignaciones con GUID nuevos. No es una plantilla de recuperacion total
tras borrar toda la suscripcion. La plantilla inicial continua bloqueada para v3.

La revision anterior `revisar_operacion.sh` sigue disponible para observar logs.
No es necesario repetirla ahora: la evidencia ya esta en `infra/azure/base_operativa.json`.

## Interpretacion de la revision

- `MARCADOR_LOCALIZADO`: encontro el marcador de diagnostico de esa ejecucion.
  No sustituye validar los valores del diagnostico ni demuestra ETL o escritura.
- `EVIDENCIA_NO_LOCALIZADA` (salida 3): no encontro el marcador. Revisar las
  rutas y el resultado por tabla antes de iniciar otra ejecucion.
- `REVISION_INCOMPLETA` (salida 2): suscripcion, permiso, respuesta o recurso
  impiden concluir. Un error nunca se convierte en una lista vacia.
- `registros_ventana`: conteo del workspace en la ventana, puede incluir otros
  recursos. `registros_ejecucion` exige coincidencia con la ejecucion elegida.
- Una tabla ausente puede ser normal: `log-analytics` usa las tablas `_CL`;
  `azure-monitor` puede usar las tablas sin sufijo. Se consultan ambas familias
  y se informan errores por separado. No interpretar cualquier error como tabla ausente.

La revision consulta configuracion de diagnostico de entorno y Job. La ausencia
de diagnostic settings NO prueba fallo cuando se usa la ruta directa antigua.
Si hay errores de permisos, conservar su codigo y corregir solo el alcance
necesario; no conceder Owner para resolver una consulta.

## Secuencia de cierre y criterios de aceptacion

1. **Logs comprobados:** conservar el marcador encontrado como evidencia.
   La ruta directa antigua funciona, pero la API subyacente termino soporte el
   2026-09-14 segun Microsoft. Preparar [migracion controlada](MIGRACION_LOGS_AZURE.md)
   al mismo workspace. No cambiar el destino ni iniciar pruebas en esta entrega.
2. **Configuracion reproducible:** reconciliar plantilla con `westus2`, v3,
   Consumption, digest privado, comando Python, ACR, identidades, permisos y
   logs efectivos. Revisar what-if sin reemplazo del lago/entorno. El script
   inicial ahora bloquea un entorno v3 existente porque aun no representa
   todos estos ajustes; no eludir este bloqueo desplegando Bicep directamente.
3. **Operacion recuperable:** recuperar estado desde Azure al reconectar;
   antes de permitir nuevos lanzamientos, impedir solapamientos, limitar
   reintentos a fallos transitorios y conservar identidad de cada ejecucion.
   El nuevo script solo observa: el lanzador antiguo aun no implementa todo esto.
4. **Alertas:** verificar estado de ejecuciones aunque falten logs; avisar
   de fallo, timeout, ausencia de corrida programada cuando exista calendario,
   interrupcion de logs y umbrales de gasto. Definir receptor antes de habilitar
   notificaciones. Probar un fallo controlado y su recuperacion. No hay alertas
   nuevas habilitadas por esta entrega.
5. **Aceptacion:** exito con salida persistida, fallo detectado, recuperacion
   tras desconexion, restauracion ensayada, presupuesto y credito documentados.
   Entonces pasar al procesamiento real que alimentara Geoda y Amatista.

## Base conocida y diferencias por reconciliar

| Elemento | Evidencia reportada | Pendiente |
|---|---|---|
| Entorno v3 | WorkloadProfiles/Consumption, westus2, Succeeded | Configuracion completa en IaC |
| ACR g7bacr09b52a0e | Basic, administrador deshabilitado | Representarlo y verificar deriva |
| Publicacion | GitHub + OIDC; ACR Tasks rechazado | Mantener esta ruta; no repetir ACR Tasks |
| Job | Manual, identidad system, imagen por digest y marcador persistido | What-if, recuperacion y ausencia de solapamientos |
| Workspace | g7b-logs-laboratorio; entrega log-analytics acreditada | Preparar migracion y comprobar retencion/coste efectivos |
| Lago | Metadatos enumerados por el auditor antes de terminar | Resultado agregado; contenido/escritura fuera de alcance |
| Credenciales y presupuesto | Usuario indico revision previa | Conservar evidencia; no repetir rotacion a ciegas |

La ejecucion `g7b-smoke-laboratorio-a665997` termino `Succeeded` de
16:48:30 a 16:49:03 UTC del 2026-11-02. El worker configurado solo termina con
exito despues de enumerar metadatos: evidencia indirecta de esa operacion,
distinta del smoke publico inicial. La revision posterior localizo un marcador
de ESA ejecucion. Los vacios anteriores no demuestran una averia; no se conoce
su causa. No afirmar revocacion SAS por un run GitHub 404.

No migrar a otras nubes ni agregar monitoreo duplicado durante este cierre.
ACR y almacenamiento de logs pueden costar aun sin ejecutar Jobs. Un presupuesto
avisa; no es un corte automatico. La operacion prevista es por excepcion, con
revision periodica de gasto, credito, permisos y actualizaciones.

Referencias:
- [Opciones de logs](https://learn.microsoft.com/en-us/azure/container-apps/log-options)
- [Migracion de la ruta antigua](https://learn.microsoft.com/azure/container-apps/migrate-logs-azure-monitor?pivots=azure-portal)
- [API de consulta](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/api/request-format)
