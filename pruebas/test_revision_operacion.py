"""Contratos del diagnostico, sin Azure ni SDK externos."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("revision", Path(__file__).resolve().parents[1] / "infra/azure/revisar_operacion.py")
revision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(revision)


class RevisionTests(unittest.TestCase):
    def test_recupera_ultima_sin_variable_de_shell(self):
        older = {"name": revision.JOB + "-anterior", "start": "2026-11-02T08:00:00Z"}
        newer = {"name": revision.JOB + "-nuevo", "start": "2026-11-02T16:48:30+00:00"}
        self.assertEqual(revision.select_execution([newer, older]), newer)
        self.assertEqual(revision.select_execution([newer, older], older["name"]), older)

    def test_no_inventa_ejecucion_ausente(self):
        with self.assertRaises(revision.RevisionError):
            revision.select_execution([])
        with self.assertRaises(revision.RevisionError):
            revision.select_execution([], revision.JOB + "-ausente")

    def test_rechaza_inyeccion_en_nombre(self):
        with self.assertRaises(revision.RevisionError):
            revision.log_query(revision.TABLES[0], "x'; union *", "", "")

    def test_consulta_delimita_ejecucion_y_no_devuelve_texto(self):
        query = revision.log_query(revision.TABLES[0], revision.JOB + "-a665997", "2026-11-02T16:43:30Z", "2026-11-02T17:04:03Z")
        self.assertIn("between (datetime(2026-11-02T16:43:30Z)", query)
        self.assertIn("startswith 'g7b-smoke-laboratorio-a665997-'", query)
        self.assertIn("countif(de_ejecucion and marcador)", query)
        self.assertNotIn("project mensaje", query)

    @patch.object(revision.subprocess, "run")
    def test_error_no_es_lista_vacia_ni_expone_stderr(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, "", "Forbidden sig=NO_PUBLICAR")
        with self.assertRaisesRegex(revision.RevisionError, "Forbidden") as ctx:
            revision.az("account", "show")
        self.assertNotIn("NO_PUBLICAR", str(ctx.exception))

    @patch.object(revision, "az")
    def test_rechaza_resultado_parcial(self, az):
        az.return_value = {"error": {"code": "PartialError"}, "tables": []}
        with self.assertRaisesRegex(revision.RevisionError, "PARCIAL"):
            revision.query_logs("workspace", "query", "start", "end")

    @patch.object(revision, "az")
    def test_cero_es_respuesta_valida(self, az):
        az.return_value = {"tables": [{"name": "PrimaryResult", "columns": [
            {"name": "registros_ejecucion"}, {"name": "diagnosticos_ejecucion"}], "rows": [[0, 0]]}]}
        self.assertEqual(revision.query_logs("workspace", "query", "start", "end")["registros_ejecucion"], 0)
        body = json.loads(az.call_args.args[-1])
        self.assertEqual(body["timespan"], "start/end")

    @patch.object(revision, "az")
    def test_suscripcion_incorrecta_detiene_antes_de_consultar_recursos(self, az):
        az.return_value = {"id": "otra", "state": "Enabled"}
        with self.assertRaisesRegex(revision.RevisionError, "SUSCRIPCION"):
            revision.main([])
        self.assertEqual(az.call_count, 1)


if __name__ == "__main__":
    unittest.main()
