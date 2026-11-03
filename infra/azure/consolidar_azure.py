"""Verifica la base conocida y prepara what-if. Nunca aplica ni inicia Jobs."""
import argparse
import json
from pathlib import Path
import tempfile

from revisar_operacion import az, get, emit, RevisionError, SUBSCRIPTION, GROUP, ENV, JOB

HERE = Path(__file__).resolve().parent
BASE = json.loads((HERE / "base_operativa.json").read_text(encoding="utf-8"))
ROOT = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{GROUP}"
ENV_ID = ROOT + "/providers/Microsoft.App/managedEnvironments/" + ENV
JOB_ID = ROOT + "/providers/Microsoft.App/jobs/" + JOB
ACR_ID = ROOT + "/providers/Microsoft.ContainerRegistry/registries/g7bacr09b52a0e"
WORKSPACE_ID = ROOT + "/providers/Microsoft.OperationalInsights/workspaces/g7b-logs-laboratorio"
PUBLISHER_ID = ROOT + "/providers/Microsoft.ManagedIdentity/userAssignedIdentities/g7b-github-acr"
STORAGE_ID = ROOT + "/providers/Microsoft.Storage/storageAccounts/g7blago09b52a0e"
BLOB_ID = STORAGE_ID + "/blobServices/default/containers/lago"
ROLES = {"AcrPull": "7f951dda-4ed3-4680-a7ca-43fe172d538d",
         "AcrPush": "8311e382-0749-4cb8-b61a-304f252e45ec",
         "Reader": "acdd72a7-3385-48ef-bd42-f606fba81ae7",
         "Storage Blob Data Reader": "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1"}


def require(condition, message):
    if not condition:
        raise RevisionError(message)


def region(value):
    return str(value).replace(" ", "").lower()


def check_job(job):
    require(region(job.get("location")) == "westus2", "REGION_JOB_DIFERENTE")
    require(job.get("state") == "Succeeded", "JOB_NO_ESTABLE")
    require(job.get("identity") == "SystemAssigned", "IDENTIDAD_JOB_DIFERENTE")
    require(job.get("environment", "").lower() == ENV_ID.lower(), "ENTORNO_JOB_DIFERENTE")
    config = job.get("config") or {}
    require(config.get("triggerType") == "Manual" and config.get("replicaTimeout") == 600
            and config.get("replicaRetryLimit") == 0, "LIMITES_JOB_DIFERENTES")
    require(config.get("manualTriggerConfig") == {"parallelism": 1, "replicaCompletionCount": 1},
            "PARALELISMO_DIFERENTE")
    require(not config.get("secrets") and not config.get("eventTriggerConfig")
            and not config.get("scheduleTriggerConfig"), "CONFIGURACION_ADICIONAL_NO_MODELADA")
    registries = config.get("registries") or []
    require(len(registries) == 1 and registries[0].get("server") == "g7bacr09b52a0e.azurecr.io"
            and registries[0].get("identity") == "system"
            and not registries[0].get("passwordSecretRef") and not registries[0].get("username"),
            "REGISTRO_JOB_DIFERENTE")
    template = job.get("template") or {}
    require(not template.get("volumes") and not template.get("initContainers"), "VOLUMENES_O_INIT_NO_MODELADOS")
    containers = template.get("containers") or []
    require(len(containers) == 1, "NUMERO_CONTENEDORES_DIFERENTE")
    c = containers[0]
    require(c.get("name") == "smoke" and c.get("image") == BASE["image"], "IMAGEN_JOB_DIFERENTE")
    require(c.get("command") == ["python"] and c.get("args") == ["/opt/g7b/g7b_ops/auditoria.py"],
            "ARRANQUE_JOB_DIFERENTE")
    expected = [{"name": "AZURE_STORAGE_ACCOUNT_URL", "value": "https://g7blago09b52a0e.blob.core.windows.net"},
                {"name": "AZURE_CONTAINER_NAME", "value": "lago"}]
    actual = c.get("env") or []
    require(len(actual) == 2 and not any(x.get("secretRef") for x in actual)
            and {x.get("name"): x.get("value") for x in actual} == {x["name"]: x["value"] for x in expected},
            "VARIABLES_JOB_DIFERENTES_NO_SE_IMPRIMEN")
    resources = c.get("resources") or {}
    require(resources.get("cpu") == 0.25 and resources.get("memory") == "0.5Gi", "RECURSOS_JOB_DIFERENTES")
    require(not c.get("probes") and not c.get("volumeMounts"), "CONFIGURACION_CONTENEDOR_NO_MODELADA")
    require(job.get("profile") in (None, "", "Consumption"), "PERFIL_JOB_DIFERENTE")


def check_role(assignments, scope, principal, name):
    matches = [x for x in assignments if x.get("scope", "").lower() == scope.lower()
               and x.get("principalId", "").lower() == principal.lower()
               and x.get("roleDefinitionId", "").lower().endswith("/" + ROLES[name])]
    require(bool(matches), "ROL_NO_ENCONTRADO_EN_ALCANCE_EXACTO: " + name)
    emit("PERMISO_EXISTENTE", {"rol": name, "alcance": scope, "asignaciones": len(matches)})


def what_if(template, parameters):
    emit("PREPARANDO_PLAN", {"plantilla": template, "limite_segundos": 600,
                             "nota": "Azure puede tardar varios minutos; no se aplican cambios."})
    # Temporal privado, fuera del repositorio, sin secretos. Siempre Incremental.
    with tempfile.TemporaryDirectory(prefix="g7b-plan-") as tmp:
        file = Path(tmp) / "parameters.json"
        file.write_text(json.dumps({"$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
                                    "contentVersion": "1.0.0.0", "parameters": {k: {"value": v} for k, v in parameters.items()}}))
        plan = az("deployment", "group", "what-if", "--resource-group", GROUP,
                  "--mode", "Incremental", "--template-file", str(HERE / template),
                  "--parameters", "@" + str(file), "--no-pretty-print", timeout_seconds=600)
    require(plan.get("status") == "Succeeded", "WHAT_IF_NO_COMPLETADO")
    changes = plan.get("changes") or []
    # Mostrar propiedades cambiadas sin valores que pudieran contener secretos.
    emit("PLAN", {"plantilla": template, "cambios": [
        {"recurso": c.get("resourceId"), "tipo": c.get("changeType"),
         "propiedades": [d.get("path") for d in (c.get("delta") or [])]} for c in changes]})
    require(not any(c.get("changeType") in ("Delete", "Create") and
                    "/diagnosticsettings/" not in c.get("resourceId", "").lower() for c in changes),
            "PLAN_REQUIERE_REVISION: creacion o eliminacion de recurso base")
    require(not any(c.get("changeType") in ("Unsupported", "Deploy") for c in changes),
            "PLAN_REQUIERE_REVISION: cambios no resueltos")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="Anade what-if del Job; nunca aplica")
    parser.add_argument("--plan-logs", action="store_true", help="Anade what-if de la ruta candidata; no cambia destino")
    args = parser.parse_args(argv)
    account = az("account", "show", "--query", "{id:id,state:state}")
    require(account.get("id") == SUBSCRIPTION and account.get("state") == "Enabled", "SUSCRIPCION_INCORRECTA")
    env = get(ENV_ID, "2026-07-01", "{location:location,state:properties.provisioningState,mode:properties.environmentMode,profiles:properties.workloadProfiles,destination:properties.appLogsConfiguration.destination,workspace:properties.appLogsConfiguration.logAnalyticsConfiguration.customerId}")
    require(region(env.get("location")) == "westus2" and env.get("state") == "Succeeded"
            and env.get("mode") == "WorkloadProfiles", "ENTORNO_DIFERENTE")
    require(any(x.get("name") == "Consumption" and x.get("workloadProfileType") == "Consumption"
                for x in (env.get("profiles") or [])), "PERFIL_CONSUMPTION_AUSENTE")
    require(env.get("destination") == "log-analytics" and env.get("workspace") == BASE["workspaceCustomerId"],
            "RUTA_CAMBIO_RESPECTO_A_BASE: revisar y versionar antes de continuar")
    emit("ENTORNO_BASE", env)
    # Solo consulta config/template; secretos de Job son referencias, no se imprimen.
    job = get(JOB_ID, "2024-03-01", "{location:location,state:properties.provisioningState,identity:identity.type,principal:identity.principalId,environment:properties.environmentId,config:properties.configuration,template:properties.template,profile:properties.workloadProfileName,tags:tags}")
    check_job(job)
    emit("JOB_BASE", {"estado": "COINCIDE", "imagen": BASE["image"]})
    acr = get(ACR_ID, "2025-11-01", "{location:location,state:properties.provisioningState,sku:sku.name,admin:properties.adminUserEnabled,mode:properties.roleAssignmentMode,arm:properties.policies.azureADAuthenticationAsArmPolicy.status}")
    require(region(acr.get("location")) == "westus2" and acr.get("state") == "Succeeded"
            and acr.get("sku") == "Basic" and acr.get("admin") is False
            and acr.get("mode") == "LegacyRegistryPermissions" and acr.get("arm") == "enabled", "ACR_DIFERENTE")
    workspace = get(WORKSPACE_ID, "2023-09-01", "{customerId:properties.customerId,retention:properties.retentionInDays,sku:properties.sku.name,quota:properties.workspaceCapping}")
    require(workspace.get("customerId") == BASE["workspaceCustomerId"], "WORKSPACE_DIFERENTE")
    emit("WORKSPACE", workspace)
    storage = get(STORAGE_ID, "2023-05-01", "{location:location,publicBlobs:properties.allowBlobPublicAccess,https:properties.supportsHttpsTrafficOnly,tls:properties.minimumTlsVersion}")
    require(region(storage.get("location")) == "westus2" and storage.get("publicBlobs") is False
            and storage.get("https") is True and storage.get("tls") == "TLS1_2", "PROTECCION_STORAGE_DIFERENTE")
    emit("STORAGE_BASE", storage)
    publisher = get(PUBLISHER_ID, "2023-01-31", "{principal:properties.principalId}")
    subject = "repo:Maximiliano-cabello-mata@335839614/amatista-g7b-etl@1441384047:ref:refs/heads/chatgpt/g7b-arquitectura-privada-ofertas-20261101"
    federation = get(PUBLISHER_ID + "/federatedIdentityCredentials/github-pr9", "2023-01-31", "properties")
    require(federation.get("subject") == subject and federation.get("issuer") == "https://token.actions.githubusercontent.com"
            and federation.get("audiences") == ["api://AzureADTokenExchange"], "FEDERACION_DIFERENTE")
    for scope, principal, names in ((ACR_ID, job["principal"], ["AcrPull"]),
                                    (ACR_ID, publisher["principal"], ["AcrPush", "Reader"]),
                                    (BLOB_ID, job["principal"], ["Storage Blob Data Reader"])):
        assignments = az("role", "assignment", "list", "--scope", scope, "--query",
                         "[].{scope:scope,principalId:principalId,roleDefinitionId:roleDefinitionId}")
        for name in names:
            check_role(assignments, scope, principal, name)
    runs = get(JOB_ID + "/executions", "2024-03-01", "value[].{name:name,status:properties.status}")
    active = [x for x in runs if x.get("status") not in ("Succeeded", "Failed", "Stopped")]
    emit("EJECUCIONES_ACTIVAS_O_DESCONOCIDAS", active)
    require(not active, "NO_PREPARAR_CAMBIOS_CON_EJECUCIONES_ACTIVAS_O_ESTADO_DESCONOCIDO")
    if args.plan:
        what_if("g7b-operacion.bicep", {"jobTags": job.get("tags") or {}, "workloadProfileName": job.get("profile") or ""})
    if args.plan_logs:
        provider = az("provider", "show", "--namespace", "Microsoft.Insights", "--query", "registrationState")
        require(provider == "Registered", "MICROSOFT_INSIGHTS_NO_REGISTRADO: no se registra automaticamente")
        categories = get(ENV_ID + "/providers/Microsoft.Insights/diagnosticSettingsCategories", "2021-05-01-preview", "value[].name")
        require({"ContainerAppConsoleLogs", "ContainerAppSystemLogs"} <= set(categories), "CATEGORIAS_LOGS_NO_DISPONIBLES")
        settings = get(ENV_ID + "/providers/Microsoft.Insights/diagnosticSettings", "2021-05-01-preview", "value[].name")
        require(not settings, "RUTAS_EXISTENTES: revisar antes de crear una ruta duplicada")
        what_if("g7b-ruta-logs.bicep", {})
    emit("CONSOLIDACION", {"estado": "BASE_COMPROBADA", "cambios_aplicados": False,
                            "ejecuciones_iniciadas": 0, "alertas_verificadas": False,
                            "limite": "Permisos requeridos presentes; no es auditoria exhaustiva de privilegios heredados."})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RevisionError as exc:
        emit("CONSOLIDACION_DETENIDA", {"motivo": str(exc), "cambios_aplicados": False})
        raise SystemExit(2)
