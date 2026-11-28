from pathlib import Path
import re

import duckdb
import pytest

from herramientas.revisar_contrato_unidades import revisar


RAIZ = Path(__file__).resolve().parents[1]
COMUNIDAD = ("writing-skills", "data-quality-frameworks", "scientific-critical-thinking", "evaluate-skill")


@pytest.mark.parametrize("nombre", COMUNIDAD)
def test_habilidad_descubrible_con_fuentes_y_referencias(nombre):
    archivo = RAIZ / ".agents/skills" / nombre / "SKILL.md"
    contenido = archivo.read_text(encoding="utf-8")
    assert contenido.startswith(f"---\nname: {nombre}\ndescription: ")
    assert re.search(r"\n---\n", contenido)
    assert re.search(r"https://github\.com/[^)]+/blob/[a-f0-9]{40}/[^)]+/SKILL\.md", contenido)
    for enlace in re.findall(r"\]\(([^)]+)\)", contenido):
        if not enlace.startswith("https://"):
            assert (archivo.parent / enlace).resolve().is_file(), enlace


def test_contrato_unidades(tmp_path):
    ruta = tmp_path / "cubo.duckdb"
    with duckdb.connect(str(ruta)) as con:
        con.execute("CREATE TABLE mediciones (fuente VARCHAR, metrica VARCHAR, unidad VARCHAR)")
    assert revisar(ruta)["filas"] == 0
    with duckdb.connect(str(ruta)) as con:
        con.executemany("INSERT INTO mediciones VALUES (?, ?, ?)", [
            ("sonda", "tiempo_edicion", "s"),
            ("blender-open-data", "samples_per_minute", "samples/min"),
            ("sonda", "cuadros_por_segundo_vista3d", "s"),
            ("sonda", "cuadros_por_segundo_vista3d", "s"),
            ("sonda", "tiempo_edicion", None),
            ("sonda", "nueva", "s"),
            ("otro", "tiempo_edicion", "s")])
    r = revisar(ruta)
    assert (r["filas"], r["conformes"], r["incompatibles"], r["sin_regla"]) == (7, 2, 3, 2)
    assert {tuple(h[k] for k in ("metrica", "observada", "esperada", "filas"))
            for h in r["hallazgos"] if h["resultado"] == "incompatibles"} == {
                ("cuadros_por_segundo_vista3d", "s", "fps", 2), ("tiempo_edicion", None, "s", 1)}


def test_archivo_inexistente(tmp_path):
    ruta = tmp_path / "ausente.duckdb"
    with pytest.raises(duckdb.Error):
        revisar(ruta)
    assert not ruta.exists()
