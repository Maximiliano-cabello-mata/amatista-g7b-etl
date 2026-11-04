"""Pruebas de los cimientos de Geoda: contratos, niveles, perfiles desde el cubo, costos y plan."""
import json

import duckdb
import pytest

from geoda import contratos, costos, niveles, perfiles, planificador
from geoda.__main__ import main as cli
from geoda.contratos import Gpu, Huella

INTEGRADA = {"cpu": "Intel i5-8250U", "ram_gb": 8, "gpus": [{"nombre": "Intel UHD 620", "tipo": "integrada"}],
             "opengl": 4.6, "so": "Windows", "arquitectura": "x86_64"}


# ---------------------------------------------------------------- contratos

def test_huella_rechaza_datos_personales_y_da_id_estable():
    with pytest.raises(ValueError):
        Huella.desde_dict({**INTEGRADA, "usuario": "maria"})
    a, b = Huella.desde_dict(INTEGRADA), Huella.desde_dict(dict(INTEGRADA, ram_gb=8.2))
    assert a.id() == b.id() and len(a.id()) == 16  # la RAM se redondea


def test_huella_desde_el_equipo_de_la_sonda():
    equipo = {"cpu": "AMD Ryzen 5", "ram_gb": 16, "so": "Linux", "arquitectura": "x86_64", "huella": "abc",
              "gpu_vista": {"modelo": "NVIDIA GeForce GTX 1650", "version": "4.6.0 NVIDIA 550"},
              "gpu_cycles": [{"tipo": "CUDA", "nombre": "NVIDIA GeForce GTX 1650"}]}
    h = Huella.desde_dict(equipo)
    assert h.gpus[0].tipo == "dedicada" and h.opengl == 4.6
    assert contratos.version_opengl("3.3 (Core Profile) Mesa") == 3.3 and contratos.version_opengl("") is None


# ---------------------------------------------------------------- niveles

@pytest.mark.parametrize("huella, nivel", [
    ({"so": "Android", "movil": True}, "N0"),
    ({**INTEGRADA, "opengl": 3.3}, "N1"),                     # sin OpenGL 4.3
    ({**INTEGRADA, "ram_gb": 4}, "N1"),                       # poca RAM: cuenta el más bajo
    (INTEGRADA, "N2"),
    ({**INTEGRADA, "gpus": [{"nombre": "GTX 1650", "tipo": "dedicada", "vram_gb": 4}]}, "N3"),
    ({**INTEGRADA, "ram_gb": 32, "gpus": [{"nombre": "RTX 3060", "tipo": "dedicada", "vram_gb": 12}]}, "N4"),
    ({**INTEGRADA, "ram_gb": 6, "gpus": [{"nombre": "RTX 3060", "tipo": "dedicada", "vram_gb": 12}]}, "N1"),
])
def test_niveles_segun_fichas_tecnicas(huella, nivel):
    assert niveles.clasificar(huella).nivel == nivel


def test_sin_datos_no_inventa_y_baja_la_confianza():
    c = niveles.clasificar({"cpu": "x", "so": "Linux"})
    assert c.nivel == "N2" and c.confianza == "baja"
    assert any("sin dato de OpenGL" in m for m in c.motivos)
    assert niveles.clasificar(Huella(cpu="x", ram_gb=16, gpus=[Gpu("RTX", "dedicada")])).confianza == "media"


# ---------------------------------------------------------------- perfiles

def cubo_falso(filas):
    """La vista v_mediciones_aceptadas del cubo (g7b_almacen/cubo.py), con solo las columnas que usa Geoda."""
    con = duckdb.connect()
    con.execute("CREATE TABLE v_mediciones_aceptadas (fuente VARCHAR, metrica VARCHAR, prueba VARCHAR, "
                "unidad VARCHAR, valor DOUBLE, version VARCHAR, perfil VARCHAR, dispositivo VARCHAR)")
    con.executemany("INSERT INTO v_mediciones_aceptadas VALUES (?, ?, ?, ?, ?, ?, ?, ?)", filas)
    con.execute("ALTER TABLE v_mediciones_aceptadas ADD COLUMN sin_ventana BOOLEAN DEFAULT FALSE")
    return con


def fila(nivel, perfil, fps, equipo, version="4.5.3"):
    dispositivo = json.dumps({"fuente": "sonda", "equipo": {"huella": equipo, "nivel": nivel}})
    return ("sonda", "cuadros_por_segundo_vista3d", "vista3d", "fps", fps, version, perfil, dispositivo)


def test_perfiles_desde_el_cubo_eligen_lo_mas_completo_que_es_fluido():
    filas = [fila("N2", "completo", 18, f"e{i}") for i in range(5)]
    filas += [fila("N2", "ligero", 34 + i, f"e{i % 3}") for i in range(5)]      # 5 mediciones, 3 equipos
    filas += [fila("N1", "minimo", 12, "v1")]                                     # nada es fluido en N1
    filas += [("blender-open-data", "samples_per_minute", "render_cycles", "samples/min", 99, "4.5", "no_aplica", "{}")]
    mediciones, sin_nivel = perfiles.leer_cubo(cubo_falso(filas))
    doc = perfiles.generar(mediciones, sin_nivel)
    assert contratos.validar_perfiles(doc) == []
    n2 = perfiles.elegir(doc, "N2", "4.5")
    assert (n2["perfil"], n2["estado"], n2["evidencia"]["equipos"]) == ("ligero", "confiable", 3)
    n1 = perfiles.elegir(doc, "N1")
    assert (n1["perfil"], n1["estado"]) == ("minimo", "provisional") and "30 fps" in n1["nota"]
    assert perfiles.elegir(doc, "N4")["estado"] == "base"           # sin mediciones: regla base
    assert perfiles.elegir(doc, "N0")["programa"] == "editor_web"


def test_mediciones_sin_nivel_ni_gpu_no_cuentan():
    sin = ("sonda", "cuadros_por_segundo_vista3d", "vista3d", "fps", 40, "4.5", "ligero",
           json.dumps({"equipo": {"huella": "x", "cpu": "y"}}))
    mediciones, sin_nivel = perfiles.leer_cubo(cubo_falso([sin]))
    assert mediciones == [] and sin_nivel == 1


def test_confiable_exige_evidencia():
    doc = perfiles.generar()
    doc["perfiles"][0].update(estado="confiable", evidencia={"mediciones": 1, "equipos": 1})
    assert any("confiable" in e for e in contratos.validar_perfiles(doc))


def test_vista_sin_ventana_no_alimenta_perfiles():
    con = cubo_falso([fila("N2", "ligero", 100, "e1")])
    con.execute("UPDATE v_mediciones_aceptadas SET sin_ventana=true")
    assert perfiles.leer_cubo(con) == ([], 0)
    con.close()


def test_ejecucion_rechaza_cubo_alterado(tmp_path):
    from geoda.ejecutar import ejecutar
    (tmp_path / "oro").mkdir()
    (tmp_path / "oro/cubo.duckdb").write_bytes(b"alterado")
    meta = {"contrato": "g7b.cubo/1", "archivos": {"oro/cubo.duckdb": {"sha256": "0" * 64}}}
    (tmp_path / "manifiesto.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="huella"):
        ejecutar(tmp_path, tmp_path / "salida")
    assert not (tmp_path / "salida").exists()


# ---------------------------------------------------------------- costos y plan

def test_costos_responden_sin_datos_en_lugar_de_inventar():
    tabla = costos.TablaCostos.desde_cubo(cubo_falso([fila("N2", "ligero", 30, "e1"), fila("N2", "ligero", 40, "e2")]))
    medido = tabla.estimar("vista3d", "N2", "ligero")
    assert (medido.valor, medido.mediciones, medido.fuente) == (35.0, 2, "cubo")
    assert tabla.estimar("booleana", "N2").fuente == "sin_datos"
    with pytest.raises(KeyError):
        tabla.estimar("teletransportar", "N2")


def test_plan_para_un_equipo_modesto_es_reversible_y_explicado():
    plan = planificador.decidir(INTEGRADA, {"tipo": "practica", "blender": "4.5"})
    assert plan["contrato"] == "g7b.plan/1" and plan["clasificacion"]["nivel"] == "N2"
    assert plan["donde"] == "este_equipo" and plan["perfil"]["perfil"] == "ligero"
    rutas = {a["ruta"] for a in plan["acciones"]}
    assert {"scene.render.use_simplify", "scene.render.simplify_subdivision"} <= rutas
    assert "deshacer" in plan and "N2" in plan["explicacion"] and "sugerido" in plan["explicacion"]


def test_plan_en_celular_manda_al_editor_web():
    plan = planificador.decidir({"so": "Android", "movil": True})
    assert plan["donde"] == "editor_web" and plan["acciones"] == []


def test_cli_nivel_y_perfiles(tmp_path, capsys):
    huella = tmp_path / "equipo.json"
    huella.write_text(json.dumps(INTEGRADA), encoding="utf-8")
    cli(["nivel", "--huella", str(huella)])
    assert json.loads(capsys.readouterr().out)["nivel"] == "N2"
    salida = tmp_path / "perfiles.json"
    cli(["perfiles", "--salida", str(salida)])
    assert json.loads(salida.read_text(encoding="utf-8"))["contrato"] == "g7b.perfil/1"


def test_de_punta_a_punta_con_el_cubo_real(tmp_path):
    """La captura conserva el nivel → el cubo de g7b_almacen → perfiles de Geoda."""
    from g7b_almacen.cubo import construir

    def medicion(i, nivel, fps, equipo):
        return {'id': f'{i:064x}', 'huella_origen': 'a' * 64, 'contrato': 'g7b.telemetria/1', 'sintetico': False,
                'fuente': 'sonda', 'estado': 'aceptado', 'fecha': '2026-11-03T00:00:00Z', 'version': '4.5.3',
                'escena': 'media', 'perfil': 'ligero', 'sonda': '0.2.0', 'metrica': 'cuadros_por_segundo_vista3d',
                'unidad': 'fps', 'valor': fps, 'motivos': [], 'variacion': .01, 'valores': [fps] * 3,
                'prueba': 'vista3d', 'licencia': 'propia', 'sin_ventana': False,
                'equipo': {'cpu': 'CPU', 'so': 'Linux', 'huella': equipo, 'nivel': nivel}}

    entradas = [('lote', medicion(i, 'N2', 31 + i, f'e{i % 3}')) for i in range(6)]
    construir(entradas, tmp_path)
    with duckdb.connect(str(tmp_path / 'oro/cubo.duckdb'), read_only=True) as con:
        mediciones, sin_nivel = perfiles.leer_cubo(con)
        tabla = costos.TablaCostos.desde_cubo(con)
    doc = perfiles.generar(mediciones, sin_nivel)
    n2 = perfiles.elegir(doc, 'N2', '4.5')
    assert (n2['perfil'], n2['estado'], n2['evidencia']['mediciones']) == ('ligero', 'confiable', 6)
    assert tabla.estimar('vista3d', 'N2', 'ligero').fuente == 'cubo'
