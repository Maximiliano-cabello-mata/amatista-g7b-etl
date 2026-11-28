"""La vuelta semanal se recupera con GitHub simulado, sin lanzar trabajos reales."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.skipif(shutil.which("bash") is None or os.name == "nt", reason="el ciclo corre en Ubuntu")
@pytest.mark.parametrize(("completadas", "fallo", "esperadas"), [
    ("", "", ["telemetria.yml", "cubo.yml"]),
    ("Cubo semanal G7B 2026-11-24", "", []),
    ("Cubo semanal G7B 2026-11-17", "telemetria.yml", ["telemetria.yml"]),
])
def test_recuperar_el_martes_tarde(tmp_path, completadas, fallo, esperadas):
    gh = tmp_path / "gh"
    gh.write_text("""#!/bin/bash
case "$1 $2" in
  'api -X')
    for arg do
      if [[ "$arg" =~ workflows/([^/]+)/dispatches$ ]]; then
        wf=${BASH_REMATCH[1]}
        echo "$wf" >> "$REGISTRO"
        [[ "$wf" != "$FALLO" ]] || exit 1
        echo 456
      fi
    done ;;
  'run watch') test "$3" = 456 ;;
  'run list') echo "$COMPLETADAS" ;;
  *) exit 2 ;;
esac
""")
    gh.chmod(0o755)
    date = tmp_path / "date"
    date.write_text('#!/bin/bash\nif [[ "$*" == "-u +%F" ]]; then echo 2026-11-25; else exec /usr/bin/date "$@"; fi\n')
    date.chmod(0o755)
    registro = tmp_path / "llamadas"
    salida = tmp_path / "outputs"
    entorno = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "REGISTRO": str(registro),
               "COMPLETADAS": completadas, "FALLO": fallo, "COMPLETO": "false",
               "GH_REPO": "local/g7b", "GITHUB_OUTPUT": str(salida)}
    script = Path(__file__).resolve().parents[1] / ".github/scripts/ciclo.sh"
    subprocess.run(["bash", str(script)], env=entorno, check=True)
    assert registro.read_text().splitlines() == ["vigilar.yml", "zyte_a_lago.yml", "procesar.yml", *esperadas, "geoda_publicar.yml"]
    assert ("telemetria.yml" in salida.read_text()) == bool(fallo)
