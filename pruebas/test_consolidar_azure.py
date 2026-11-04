"""Pruebas de deriva y alcance. Sin credenciales ni llamadas a Azure."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

AZURE = Path(__file__).resolve().parents[1] / "infra/azure"
sys.path.insert(0, str(AZURE))
spec = importlib.util.spec_from_file_location("consolidar", AZURE / "consolidar_azure.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def sample():
    return {"location": "West US 2", "state": "Succeeded", "identity": "SystemAssigned",
            "environment": c.ENV_ID, "profile": None,
            "config": {"triggerType": "Manual", "replicaTimeout": 600, "replicaRetryLimit": 0,
                       "manualTriggerConfig": {"parallelism": 1, "replicaCompletionCount": 1},
                       "registries": [{"server": "g7bacr09b52a0e.azurecr.io", "identity": "system"}]},
            "template": {"containers": [{"name": "smoke", "image": c.BASE["image"],
                "command": ["python"], "args": ["/opt/g7b/g7b_ops/auditoria.py"],
                "resources": {"cpu": 0.25, "memory": "0.5Gi"},
                "env": [{"name": "AZURE_STORAGE_ACCOUNT_URL", "value": "https://g7blago09b52a0e.blob.core.windows.net"},
                        {"name": "AZURE_CONTAINER_NAME", "value": "lago"}]}]}}


class ConsolidarTests(unittest.TestCase):
    def test_normaliza_region_reportada_por_azure(self):
        c.check_job(sample())

    def test_rechaza_deriva_sin_corregirla(self):
        for field, value in (("location", "mexicocentral"), ("identity", "None"), ("profile", "Dedicated")):
            job = sample()
            job[field] = value
            with self.subTest(field=field), self.assertRaises(c.RevisionError):
                c.check_job(job)

    def test_rechaza_smoke_y_arranque_vacio(self):
        for field, value in (("image", "mcr.microsoft.com/k8se/quickstart-jobs:latest"), ("command", [""])):
            job = sample()
            job["template"]["containers"][0][field] = value
            with self.subTest(field=field), self.assertRaises(c.RevisionError):
                c.check_job(job)

    def test_no_expone_variables_desconocidas(self):
        job = sample()
        job["template"]["containers"][0]["env"].append({"name": "SECRET", "value": "NO_PUBLICAR"})
        with self.assertRaises(c.RevisionError) as ctx:
            c.check_job(job)
        self.assertNotIn("NO_PUBLICAR", str(ctx.exception))

    def test_no_elimina_volumenes_o_secretos_sin_modelar(self):
        for section, field, value in (("template", "volumes", [{"name": "extra"}]),
                                      ("config", "secrets", [{"name": "extra"}])):
            job = sample()
            job[section][field] = value
            with self.assertRaises(c.RevisionError):
                c.check_job(job)

    def test_rol_exige_principal_y_alcance_exacto(self):
        assignment = {"scope": c.ACR_ID, "principalId": "job", "roleDefinitionId": "/roles/" + c.ROLES["AcrPull"]}
        c.check_role([assignment], c.ACR_ID, "job", "AcrPull")
        for change in ({"scope": c.ROOT}, {"principalId": "otro"}):
            bad = {**assignment, **change}
            with self.assertRaises(c.RevisionError):
                c.check_role([bad], c.ACR_ID, "job", "AcrPull")

    @patch.object(c, "az")
    def test_whatif_no_aplica_y_rechaza_borrado(self, az):
        az.return_value = {"status": "Succeeded", "changes": [{"resourceId": c.JOB_ID, "changeType": "Delete"}]}
        with self.assertRaises(c.RevisionError):
            c.what_if("g7b-operacion.bicep", {"jobTags": {}})
        args = az.call_args.args
        self.assertEqual(args[:3], ("deployment", "group", "what-if"))
        self.assertIn("Incremental", args)

    @patch.object(c, "az")
    def test_whatif_permite_ruta_candidata_sin_aplicarla(self, az):
        az.return_value = {"status": "Succeeded", "changes": [{
            "resourceId": c.ENV_ID + "/providers/Microsoft.Insights/diagnosticSettings/g7b-console-system", "changeType": "Create"}]}
        c.what_if("g7b-ruta-logs.bicep", {})
        self.assertEqual(az.call_count, 1)

    @patch.object(c, "get")
    @patch.object(c, "az")
    def test_suscripcion_incorrecta_no_consulta_ni_cambia_recursos(self, az, get):
        az.return_value = {"id": "otra", "state": "Enabled"}
        with self.assertRaises(c.RevisionError):
            c.main([])
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
