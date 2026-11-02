# Cierre operativo de Azure G7B

## Estado y siguiente accion

Azure ejecuta el auditor privado. Falta comprobar entrega de logs y completar
reconciliacion de infraestructura, alertas y recuperacion. No esta cerrado.
La evidencia de Azure procede de las salidas del usuario del 2026-11-02;
las comprobaciones de CI no acceden a la suscripcion.

Desde Cloud Shell Bash, una sola revision sin modificar Azure:

```bash
cd "$HOME/g7b-cloud-shell" &&
git switch chatgpt/g7b-arquitectura-privada-ofertas-20261101 &&
git pull --ff-only &&
bash infra/azure/revisar_operacion.sh --ejecucion g7b-smoke-laboratorio-a665997
```

Si la carpeta no existe en una sesion efimera, recuperar el checkout:

```bash
git clone --branch chatgpt/g7b-arquitectura-privada-ofertas-20261101 \
  https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl.git "$HOME/g7b-cloud-shell"
```

El script usa Python 3 estandar y la sesion de Azure CLI. No instala extensiones,
no inicia Jobs, no lee claves/SAS ni cuerpos de blobs. No imprime mensajes de logs
completos: entrega conteos y configuracion seleccionada, sin variables del worker.
Sin `--ejecucion`, selecciona la mas reciente desde Azure, no desde una variable
de shell. Una ejecucion fuera del historial retenido se informa como ausente.

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

1. **Logs:** inspeccionar este informe; resolver destino, permisos o esquema
   segun evidencia. Si se migra a Azure Monitor, reutilizar el workspace,
   comprobar categorias admitidas y evitar entregas duplicadas. Ejecutar una
   unica prueba nueva despues del cambio y recuperar su resultado persistido.
   No es posible reconstruir logs que nunca se ingirieron.
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
| Job | Manual, identidad system, imagen por digest | Validar logs, recuperacion y ausencia de solapamientos |
| Workspace | g7b-logs-laboratorio; destino log-analytics | Entrega aun no acreditada |
| Lago | Metadatos enumerados por el auditor antes de terminar | Resultado agregado; contenido/escritura fuera de alcance |
| Credenciales y presupuesto | Usuario indico revision previa | Conservar evidencia; no repetir rotacion a ciegas |

La ejecucion `g7b-smoke-laboratorio-a665997` termino `Succeeded` de
16:48:30 a 16:49:03 UTC del 2026-11-02. El worker configurado solo termina con
exito despues de enumerar metadatos: evidencia indirecta de esa operacion,
distinta del smoke publico inicial. Las consultas aportadas devolvieron `[]`;
la causa sigue sin confirmar. No afirmar revocacion SAS por un run GitHub 404.

No migrar a otras nubes ni agregar monitoreo duplicado durante este cierre.
ACR y almacenamiento de logs pueden costar aun sin ejecutar Jobs. Un presupuesto
avisa; no es un corte automatico. La operacion prevista es por excepcion, con
revision periodica de gasto, credito, permisos y actualizaciones.

Referencias:
- [Opciones de logs](https://learn.microsoft.com/en-us/azure/container-apps/log-options)
- [Migracion de la ruta antigua](https://learn.microsoft.com/azure/container-apps/migrate-logs-azure-monitor?pivots=azure-portal)
- [API de consulta](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/api/request-format)
