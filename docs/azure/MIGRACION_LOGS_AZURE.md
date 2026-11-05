# Migracion preparada, aun no aplicada

## Motivo y estado

La ruta actual funciona: el usuario recupero el marcador del auditor en
ContainerAppConsoleLogs_CL. Esta migracion es mantenimiento, no reparacion de
una averia demostrada. Microsoft indica fin de soporte de la API de la ruta
directa el 2026-09-14; la ingestion puede continuar con clientes TLS compatibles.

Se prepara `g7b-ruta-logs.bicep`, que SOLO define diagnostic settings en el
entorno existente, hacia el MISMO workspace, con consola y sistema, tablas
Dedicated. No modifica el entorno, Job, permisos, imagen ni retencion.
No aplicar esa plantilla aislada ni cambiar solo el destino del entorno.

## Comprobacion previa sin cambios

```bash
bash infra/azure/consolidar_azure.sh --plan --plan-logs
```

Verifica la base operativa, ausencia de ejecuciones activas o desconocidas,
Microsoft.Insights registrado, categorias admitidas y ausencia de rutas que se
pudieran duplicar. Prepara what-if; si encuentra algo distinto, se detiene.
Si Microsoft.Insights no esta registrado, informa el bloqueo; no lo registra.
Si el proveedor no expone categorias mientras el destino sigue siendo legacy,
investigar esa respuesta antes de aplicar; no tratarla como autorizacion para
omitir la comprobacion. No se envian alertas ni se inicia otra ejecucion.

## Secuencia para una ventana posterior

1. Registrar el estado previo, revisar cualquier alerta/consulta que use `_CL`,
   permisos del operador y acceso de recuperacion al workspace sin revelar claves.
2. Preparar en conjunto el cambio del destino a `azure-monitor` y la aplicacion
   inmediata de la ruta versionada. Mantener observacion del estado del Job
   independiente de la ingestion. Conservar configuracion anterior para rollback.
3. Microsoft advierte activacion de diagnostic settings de hasta 90 minutos.
   No afirmar exito porque Azure acepte el cambio de configuracion.
4. Verificar al menos dos marcadores nuevos con timestamps crecientes y el ultimo
   de menos de diez minutos, segun la guia de migracion. Los marcadores historicos
   no prueban la nueva ruta. Usar una sonda acotada en una ventana autorizada,
   no repetir el auditor que enumera el lago solo para generar logs.
5. Solo entonces habilitar y probar alertas en las tablas nuevas. Conservar
   consultas historicas de `_CL`; no borrar el workspace ni sus tablas antiguas.
6. Si no aparecen marcadores dentro de la ventana maxima, no completar el cambio
   de alertas. Diagnosticar o restaurar la ruta directa con el mismo workspace.
   Las claves necesarias para restaurar se obtienen solo en sesion autorizada,
   nunca se guardan en Git, mensajes, parametros publicos ni salida de terminal.

La instruccion actual es NO lanzar otra ejecucion. Por eso esta entrega prepara
plantilla y plan, y no migra una ruta funcional sin poder comprobar trafico nuevo.
Faltan aplicacion en Azure, validacion de entrega posterior y ensayo de rollback.

## Alertas despues de validar la ruta

- Fallo/timeout de ejecucion: comprobar estado de Azure aunque los logs fallen.
- Ausencia de corrida: solo cuando exista un calendario esperado; hoy el Job es Manual.
- Ausencia de logs: relacionarla con una ejecucion conocida, no con inactividad normal.
- Presupuesto y credito: comprobar configuracion efectiva y destinatario. Un
  presupuesto no apaga automaticamente los recursos.

Todavia no se ha definido ni probado un receptor de alertas. No presentar este
plan como vigilancia automatica instalada. No ampliar la identidad de build a
Contributor de suscripcion para implementar monitoreo.

[Guia oficial de migracion](https://learn.microsoft.com/en-us/azure/container-apps/migrate-logs-azure-monitor?pivots=azure-portal)
