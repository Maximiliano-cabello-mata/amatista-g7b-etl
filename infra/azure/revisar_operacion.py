"""Diagnostico de solo lectura; Azure CLI autenticada, sin extensiones ni SDK extra."""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

SUBSCRIPTION = "04408599-cf01-476f-9bab-6c57566a15a4"
GROUP = "g7b"
JOB = "g7b-smoke-laboratorio"
ENV = "g7b-env-laboratorio-jobs-v3"
ARM = "https://management.azure.com"
TABLES = ("ContainerAppConsoleLogs_CL", "ContainerAppSystemLogs_CL",
          "ContainerAppConsoleLogs", "ContainerAppSystemLogs")


class RevisionError(Exception):
    pass


def az(*args, timeout_seconds=90):
    try:
        result = subprocess.run(["az", *args, "--output", "json", "--only-show-errors"],
                                capture_output=True, text=True, timeout=timeout_seconds, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RevisionError("AZ_NO_DISPONIBLE_O_TIMEOUT: comprobar sesion Cloud Shell") from exc
    if result.returncode:
        # No copiar stderr completo: puede incluir URLs firmadas o cuerpo de respuestas.
        code = "CONSULTA_FALLIDA"
        if "Failed to resolve table" in result.stderr or "Failed to resolve scalar" in result.stderr:
            code = "TABLA_O_COLUMNA_NO_DISPONIBLE"
        for token in ("AuthorizationFailed", "Forbidden", "InsufficientAccessError",
                      "ResourceNotFound", "PathNotFoundError", "InvalidAuthenticationToken",
                      "BadArgumentError", "PartialError"):
            if token in result.stderr:
                code = token
                break
        raise RevisionError(code + ": la consulta no equivale a cero registros")
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise RevisionError("RESPUESTA_NO_JSON") from exc


def get(resource, api, query):
    return az("rest", "--method", "get", "--url", f"{ARM}{resource}?api-version={api}",
              "--query", query)


def emit(label, data):
    print(label + " " + json.dumps(data, ensure_ascii=False, sort_keys=True), flush=True)


def instant(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("sin zona")
        return dt.astimezone(timezone.utc)
    except (ValueError, AttributeError) as exc:
        raise RevisionError("FECHA_DE_EJECUCION_INVALIDA") from exc


def select_execution(executions, requested=None):
    if requested:
        if not re.fullmatch(re.escape(JOB) + r"-[a-z0-9]+", requested):
            raise RevisionError("NOMBRE_DE_EJECUCION_INVALIDO")
        matches = [x for x in executions if x.get("name") == requested]
        if not matches:
            raise RevisionError("EJECUCION_NO_ENCONTRADA: comprobar historial retenido")
        return matches[0]
    candidates = [x for x in executions if x.get("start")]
    if not candidates:
        raise RevisionError("SIN_EJECUCIONES: no se inicia ninguna automaticamente")
    return max(candidates, key=lambda x: instant(x["start"]))


def log_query(table, execution, start, end):
    # Una tabla por consulta: una tabla ausente no oculta errores de las demas.
    if table not in TABLES or not re.fullmatch(re.escape(JOB) + r"-[a-z0-9]+", execution):
        raise RevisionError("CONSULTA_INVALIDA")
    return f"""{table}
| where TimeGenerated between (datetime({start}) .. datetime({end}))
| extend replica=tostring(column_ifexists('ContainerGroupName_s', column_ifexists('ContainerGroupName', ''))),
         trabajo=tostring(column_ifexists('JobName_s', column_ifexists('JobName', ''))),
         mensaje=tostring(column_ifexists('Log_s', column_ifexists('Log', '')))
| extend de_ejecucion=(replica == '{execution}' or replica startswith '{execution}-' or trabajo == '{execution}'),
         marcador=(mensaje startswith 'G7B_AZURE_DIAGNOSTICO ')
| summarize registros_ventana=count(), registros_ejecucion=countif(de_ejecucion),
            diagnosticos_ejecucion=countif(de_ejecucion and marcador),
            ultimo=max(TimeGenerated)
"""


def query_logs(workspace, query, start, end):
    data = az("rest", "--method", "post", "--url",
              f"https://api.loganalytics.io/v1/workspaces/{workspace}/query",
              "--resource", "https://api.loganalytics.io", "--body",
              json.dumps({"query": query, "timespan": f"{start}/{end}"}))
    if data.get("error"):
        raise RevisionError("CONSULTA_PARCIAL_O_FALLIDA")
    tables = data.get("tables", [])
    primary = next((t for t in tables if t.get("name") == "PrimaryResult"), None)
    if not primary or len(primary.get("rows", [])) != 1:
        raise RevisionError("FORMATO_DE_LOGS_INESPERADO")
    return dict(zip([c["name"] for c in primary["columns"]], primary["rows"][0]))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Revision Azure de solo lectura, sin lanzar trabajos")
    parser.add_argument("--ejecucion", help="Por defecto recupera la mas reciente desde Azure")
    args = parser.parse_args(argv)
    account = az("account", "show", "--query", "{id:id,name:name,state:state}")
    if account.get("id") != SUBSCRIPTION or account.get("state") != "Enabled":
        raise RevisionError("SUSCRIPCION_INCORRECTA_O_DESHABILITADA: no se cambia automaticamente")
    emit("SUSCRIPCION", {"nombre": account["name"], "estado": account["state"]})
    root = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{GROUP}"
    env_id = root + "/providers/Microsoft.App/managedEnvironments/" + ENV
    job_id = root + "/providers/Microsoft.App/jobs/" + JOB
    env = get(env_id, "2026-07-01", "{name:name,location:location,state:properties.provisioningState,mode:properties.environmentMode,profiles:properties.workloadProfiles,destination:properties.appLogsConfiguration.destination,workspace:properties.appLogsConfiguration.logAnalyticsConfiguration.customerId}")
    emit("ENTORNO", env)
    job = get(job_id, "2024-03-01", "{name:name,location:location,state:properties.provisioningState,environment:properties.environmentId,identity:identity.type,trigger:properties.configuration.triggerType,timeout:properties.configuration.replicaTimeout,retries:properties.configuration.replicaRetryLimit,registries:properties.configuration.registries[].{server:server,identity:identity},containers:properties.template.containers[].{name:name,image:image,command:command,args:args}}")
    emit("JOB", job)
    if (job.get("environment", "").lower() != env_id.lower()
            or env.get("mode") != "WorkloadProfiles"):
        raise RevisionError("ENTORNO_NO_COINCIDE_CON_LA_BASE_ESPERADA")
    executions = get(job_id + "/executions", "2024-03-01", "value[].{name:name,status:properties.status,start:properties.startTime,end:properties.endTime}")
    execution = select_execution(executions, args.ejecucion)
    emit("EJECUCION", execution)
    start = (instant(execution["start"]) - timedelta(minutes=5)).isoformat()
    end = (instant(execution["end"]) + timedelta(minutes=15) if execution.get("end")
           else datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    emit("VENTANA_UTC", {"desde": start, "hasta": end})
    destinations = []
    settings_errors = False
    for label, resource in (("ENTORNO", env_id), ("JOB", job_id)):
        try:
            settings = get(resource + "/providers/Microsoft.Insights/diagnosticSettings",
                           "2021-05-01-preview",
                           "value[].{name:name,workspace:properties.workspaceId,logs:properties.logs,tableMode:properties.logAnalyticsDestinationType}")
            emit("RUTA_" + label, settings)
            destinations.extend(x["workspace"] for x in settings if x.get("workspace"))
        except RevisionError as exc:
            settings_errors = True
            emit("RUTA_" + label, {"error": str(exc)})
    workspace_ids = set()
    if env.get("destination") == "log-analytics" and env.get("workspace"):
        workspace_ids.add(env["workspace"])
    if env.get("destination") == "azure-monitor":
        for resource in sorted(set(destinations)):
            workspace_ids.add(get(resource, "2023-09-01", "properties.customerId"))
    if not workspace_ids:
        raise RevisionError("SIN_WORKSPACE_RESUELTO: revisar las rutas anteriores; no cambiar destino a ciegas")
    evidence = False
    failures = []
    for workspace in sorted(workspace_ids):
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", workspace):
            raise RevisionError("WORKSPACE_INVALIDO")
        for table in TABLES:
            try:
                row = query_logs(workspace, log_query(table, execution["name"], start, end), start, end)
                emit("LOGS", {"workspace": workspace, "tabla": table, **row})
                evidence |= int(row.get("diagnosticos_ejecucion", 0)) > 0
            except RevisionError as exc:
                failures.append(table)
                emit("LOGS", {"workspace": workspace, "tabla": table, "error": str(exc),
                              "nota": "Tabla ausente, permisos o consulta fallida: no equivale a cero filas."})
    if evidence:
        emit("RESULTADO", {"estado": "MARCADOR_LOCALIZADO", "ejecucion": execution["name"],
                           "limite": "Confirma entrega del marcador; no valida contenido, escritura ni ETL.",
                           "revision_rutas_incompleta": settings_errors, "tablas_con_error": failures})
        return 0 if execution.get("status") == "Succeeded" else 1
    emit("RESULTADO", {"estado": "EVIDENCIA_NO_LOCALIZADA", "ejecucion": execution["name"],
                       "accion": "Revisar ruta, tablas y permisos con este informe. No reiniciar el Job.",
                       "tablas_con_error": failures})
    return 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RevisionError as exc:
        emit("REVISION_INCOMPLETA", {"error": str(exc)})
        sys.exit(2)
