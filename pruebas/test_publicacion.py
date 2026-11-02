"""Pruebas de publicación estable de G7B: nunca cambiar puntero sin calidad."""
import json

import pytest

from g7b_almacen import almacen, publicacion


def _aprobado():
    return {
        "aprobado": True,
        "generado": "2026-11-01T20:00:00+00:00",
        "checks": [{"nombre": "volumen", "estado": "ok"}],
    }


def _candidato(a, reporte):
    a.escribir("oro/perfiles.json", b'{"contrato":"g7b.perfil/1","perfiles":[]}')
    a.escribir("oro/resumen.json", b'{"conteos":{"corridas_sonda":1}}')
    a.escribir("oro/calidad.json", json.dumps(reporte).encode())


def test_publicacion_aprobada_se_verifica(tmp_path):
    a = almacen.Carpeta(tmp_path)
    reporte = _aprobado()
    _candidato(a, reporte)
    m = publicacion.publicar(a, reporte)
    assert m["calidad_aprobada"] is True
    assert publicacion.leer_actual(a)["version"] == m["version"]
    for nombre in ("perfiles", "resumen", "calidad"):
        assert a.existe(m["archivos"][nombre]["ruta"])
    # La misma entrada no crea otra versión.
    assert publicacion.publicar(a, reporte)["version"] == m["version"]


def test_reprobacion_conserva_publicacion_previa(tmp_path):
    a = almacen.Carpeta(tmp_path)
    reporte = _aprobado()
    _candidato(a, reporte)
    antes = publicacion.publicar(a, reporte)["version"]
    a.escribir("oro/perfiles.json", b'{"contrato":"g7b.perfil/1","perfiles":[{"mal":"dato"}]}')
    with pytest.raises(ValueError, match="no aprobó"):
        publicacion.publicar(a, {"aprobado": False, "checks": [{"estado": "falla"}]})
    assert publicacion.leer_actual(a)["version"] == antes


def test_no_publica_si_falta_archivo_o_reporte_es_distinto(tmp_path):
    a = almacen.Carpeta(tmp_path)
    reporte = _aprobado()
    a.escribir("oro/perfiles.json", b"{}")
    with pytest.raises(ValueError, match="Falta"):
        publicacion.publicar(a, reporte)
    _candidato(a, reporte)
    a.escribir("oro/calidad.json", json.dumps({**reporte, "aprobado": False}).encode())
    with pytest.raises(ValueError, match="no está aprobado"):
        publicacion.publicar(a, reporte)
    assert publicacion.leer_actual(a) is None


def test_detecta_snapshot_manipulado(tmp_path):
    a = almacen.Carpeta(tmp_path)
    reporte = _aprobado()
    _candidato(a, reporte)
    m = publicacion.publicar(a, reporte)
    a.escribir(m["archivos"]["perfiles"]["ruta"], b"modificado")
    with pytest.raises(ValueError, match="Integridad"):
        publicacion.leer_actual(a)


def test_cli_rechaza_cubo_vacio_y_no_publica(tmp_path):
    from g7b_almacen.__main__ import main
    with pytest.raises(SystemExit) as exc:
        main(["construir", "--carpeta", str(tmp_path)])
    assert exc.value.code == 2
    a = almacen.Carpeta(tmp_path)
    assert not a.existe(publicacion.PUNTERO)


def test_cli_publica_con_una_medicion_valida(tmp_path):
    from g7b_almacen.__main__ import main
    a = almacen.Carpeta(tmp_path)
    medicion = {
        "contrato": "g7b.medicion/1",
        "sonda": "0.2.0",
        "fecha": "2026-11-01T20:00:00+00:00",
        "origen": "colab",
        "sintetico": False,
        "completa": True,
        "blender": {"version": "4.5.15", "sin_ventana": True},
        "equipo": {"huella": "equipotest", "nivel": "N2",
                   "so": "Linux", "cpu": "CPU prueba", "ram_gb": 16},
        "escena": {"nombre": "ligera"},
        "resultados": [
            {"prueba": "animacion", "perfil": "ligero", "unidad": "fps",
             "valores": [35, 36, 37], "mediana": 36, "variacion": 0.055},
        ],
    }
    a.escribir("bronce/sonda/2026-11-01/una.json", json.dumps(medicion).encode())
    main(["construir", "--carpeta", str(tmp_path)])
    publicado = publicacion.leer_actual(a)
    assert publicado is not None
    ruta = publicado["archivos"]["perfiles"]["ruta"]
    perfiles = json.loads(a.leer(ruta))["perfiles"]
    assert perfiles[0]["estado"] == "provisional"
    assert perfiles[0]["perfil"] == "ligero"
