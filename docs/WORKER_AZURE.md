# Worker Azure: estado y operacion

El auditor privado ya reemplazo el smoke publico segun las salidas del usuario
del 2026-11-02. Sigue siendo un lector de metadatos, no el ETL Parquet/DuckDB.
La prioridad es [cerrar logs y operacion](CIERRE_AZURE.md).

## Consultar despues de una desconexion

```bash
cd "$HOME/g7b-cloud-shell" &&
git pull --ff-only &&
bash infra/azure/revisar_operacion.sh
```

No inicia trabajos. Recupera la ultima ejecucion desde Azure y revisa la entrega
de logs. Usar `--ejecucion g7b-smoke-laboratorio-a665997` para la corrida conocida
del 2 de noviembre, mientras Azure conserve su historial. Un resultado vacio
no demuestra fallo de acceso al lago ni identifica la causa de falta de logs.

## Publicar una nueva version, solo cuando cambie el worker

Usar [GitHub con OIDC](PUBLICAR_WORKER_OIDC.md): ACR Tasks fue rechazado en esta
suscripcion. No crear otro ACR, habilitar administrador ni repetir ACR Tasks.
El ACR existente es `g7bacr09b52a0e`; conservar permisos limitados al registro.

Para configurar una imagen ya publicada, `activar_diagnostico.sh --aplicar`
requiere `G7B_IMAGEN_EXISTENTE=g7b/auditoria:COMMIT_COMPLETO`, el nombre del ACR,
la suscripcion verificada y las confirmaciones previas de presupuesto y SAS.
No establecer confirmaciones como sustituto de evidencia. No repetir una
rotacion ya hecha. El script fija el digest y el comando Python y no inicia el
Job. Su ruta antigua sin G7B_IMAGEN_EXISTENTE invoca ACR Tasks: no usarla aqui.

`--ejecutar` inicia una corrida nueva; no usarlo para consultar una existente.
Antes de iniciar, comprobar que no hay otra activa. La observacion expira a
los 12 minutos y no cancela Azure. El control automatico de solapamientos queda
pendiente del cierre operativo.

## Evidencia y recuperacion

La corrida `a665997` termino Succeeded; el marcador `G7B_AZURE_DIAGNOSTICO`
aun no se recupero. El worker enumera objetos con ManagedIdentityCredential
antes de terminar: evidencia indirecta de lectura de metadatos. Su limite es
10000 objetos; cero objetos puede ser un resultado valido. No descarga cuerpos.

La corrida fallida `z1vrdd8` mostraba command/args como `[""]`. Se corrigio a
`command=["python"]`, `args=["/opt/g7b/g7b_ops/auditoria.py"]`. No volver a limpiar
estos campos pasando cadenas vacias. La causa final del fallo carece de logs.

Una restauracion debe recuperar imagen por digest, comando, argumentos y
configuracion compatibles; cambiar solo la imagen no es un rollback completo.
No redesplegar la plantilla inicial: faltan ajustes hechos directamente en Azure.
El lanzador de aprovisionamiento ahora bloquea ese caso. La restauracion completa
todavia debe ensayarse y documentarse antes de declarar Azure cerrado.
