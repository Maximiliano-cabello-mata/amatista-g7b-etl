"""Vigía (sonda continua, g7b.ventana/1): ventanas, variación y subida con firma de solo creación."""
import importlib.util
import json
import os
import sys

RUTA = os.path.join(os.path.dirname(__file__), "..", "sonda", "g7b_vigia.py")
spec = importlib.util.spec_from_file_location("g7b_vigia", RUTA)
vigia = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vigia)


def _sesion():
    return vigia.Sesion({"huella": "abc", "cpu": "Intel Core i3-10110U"}, "trabajo1", "4.5.3")


def test_ventanas_comparan_con_la_primera_y_la_anterior():
    s = _sesion()
    for i, t in enumerate([10, 10, 11]):
        s.cuadro(i, t)
    s.tomar({"cpu_pct": 90, "cpu_mhz": 2100})
    v0 = s.cerrar()
    assert v0["cuadros"]["resumen"]["mediana"] == 10 and v0["variacion"]["estado"] == "estable"
    assert v0["sistema"]["cpu_pct"]["mediana"] == 90
    for i, t in enumerate([13, 13, 14]):
        s.cuadro(i + 3, t)
    v1 = s.cerrar()
    assert v1["variacion"]["frente_a_base"] == 0.3 and v1["variacion"]["estado"] == "caida_importante"
    s.cuadro(6, 11.5)
    v2 = s.cerrar("terminado")
    assert v2["variacion"]["estado"] == "variacion" and v2["ventana"] == 2 and v2["estado"] == "terminado"
    assert v2["contrato"] == "g7b.ventana/1" and v2["sintetico"] is False


def test_ventana_sin_cuadros_no_inventa():
    v = _sesion().cerrar()
    assert v["cuadros"]["resumen"] is None and v["variacion"]["estado"] == "sin_datos"


def test_lectura_de_la_salida_de_blender():
    assert vigia.RE_TIEMPO_CUADRO.match(" Time: 00:05.42 (Saving: 00:00.03)").groups() == (None, "00", "05.42")
    assert vigia.RE_TIEMPO_CUADRO.match(" Time: 01:02:03.50 (Saving: 00:00.03)").groups() == ("01", "02", "03.50")
    assert vigia.RE_CUADRO.search("Fra:12 Mem:512.3M | Time:00:03.21").group(1) == "12"
    assert vigia.RE_TIEMPO_CUADRO.match("Fra:12 Mem:512.3M | Time:00:03.21") is None


class _Respuesta:
    status = 201
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_subida_no_sobrescribe_y_va_a_bronce():
    pedidos = []
    def abrir(pedido, timeout):
        pedidos.append(pedido)
        return _Respuesta()
    registro = _sesion().cerrar()
    assert vigia.subir(registro, "https://cuenta.blob.core.windows.net/lago?sp=c&sig=x", abrir)
    url = pedidos[0].full_url
    assert url.startswith("https://cuenta.blob.core.windows.net/lago/bronce/telemetria/vigia/")
    assert url.endswith("-0000.json?sp=c&sig=x")
    assert pedidos[0].get_header("If-none-match") == "*" and pedidos[0].get_method() == "PUT"


def test_lo_que_no_se_sube_queda_pendiente_y_se_reintenta(tmp_path):
    red = {"arriba": False}
    envio = vigia.Envio(str(tmp_path), "https://x/lago?sig", subir_fn=lambda r, u: red["arriba"], salida=lambda *_: None)
    s = _sesion()
    envio.guardar(s.cerrar())
    assert len(os.listdir(tmp_path / "pendientes")) == 1
    red["arriba"] = True
    envio.guardar(s.cerrar())
    assert os.listdir(tmp_path / "pendientes") == [] and len(os.listdir(tmp_path / "subidas")) == 2


def test_no_guarda_rutas_ni_nombres(tmp_path):
    blend = tmp_path / "proyecto_de_ana.blend"
    blend.write_bytes(b"BLENDER-v405" + b"0" * 100)
    s = vigia.Sesion(vigia.equipo(), vigia.huella_trabajo(str(blend)))
    texto = json.dumps(s.cerrar())
    assert "proyecto_de_ana" not in texto and str(tmp_path) not in texto and os.environ.get("USER", "nadie") not in texto
