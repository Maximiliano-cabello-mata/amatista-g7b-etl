import copy
import json
import zipfile

import pytest

from g7b_telemetria.capturar import capturar, opendata, registros_zip, sonda


def medicion():
    return {'contrato': 'g7b.medicion/1', 'sintetico': False, 'sonda': '0.1.0',
            'fecha': '2026-11-03T00:00:00Z', 'blender': {'version': '4.2', 'sin_ventana': True},
            'escena': {'nombre': 'ligera'}, 'equipo': {'cpu': 'prueba'}, 'repeticiones': 3,
            'completa': True, 'calentamiento_descartado': True,
            'resultados': [{'prueba': 'edicion', 'metrica': 'tiempo', 'unidad': 's',
                            'valores': [1, 1.01, 1.02], 'mediana': 1.01}]}


def benchmark():
    return {'schema_version': 'v4', 'id': '00000000-0000-0000-0000-000000000001',
            'created_at': '2026-11-03T00:00:00Z', 'data': [{
                'blender_version': {'version': '4.2'}, 'scene': {'label': 'monster'},
                'system_info': {'system': 'Linux'},
                'device_info': {'device_type': 'CPU', 'compute_devices': [{'name': 'CPU'}]},
                'stats': {'samples_per_minute': 123}}]}


def test_variacion_se_recalcula():
    d = medicion()
    assert sonda(d)[0]['estado'] == 'aceptado'
    d['resultados'][0].update(valores=[.5, 1.01, 2], variacion=0)
    assert sonda(d)[0]['estado'] == 'revision'


@pytest.mark.parametrize('valor', [float('nan'), float('inf'), -1, 0, True])
def test_rechaza_valores_imposibles(valor):
    d = benchmark()
    d['data'][0]['stats']['samples_per_minute'] = valor
    with pytest.raises(ValueError): opendata(d)


def test_no_convierte_sinteticos_ni_medianas_inconsistentes():
    d = medicion()
    d['sintetico'] = True
    with pytest.raises(ValueError): sonda(d)
    d['sintetico'] = False
    d['resultados'][0]['mediana'] = 99
    with pytest.raises(ValueError): sonda(d)


def test_fuente_publica_no_es_fps():
    fila = opendata(benchmark())[0]
    assert fila['unidad'] == 'samples/min'
    assert fila['estado'] == 'revision'
    assert fila['preguntas'] == ['P1']


def test_duplicados_reintentos_y_lectura_azure(tmp_path):
    class Lago:
        def __init__(self): self.archivos = {}
        def subir_jsonl_gz(self, ruta, datos): self.archivos.setdefault(ruta, copy.deepcopy(datos))
        def leer_jsonl_gz(self, ruta): return self.archivos[ruta]
    lago = Lago()
    r = capturar([benchmark(), benchmark()], 'blender-open-data', tmp_path, lago=lago)
    assert r['conteos']['duplicados'] == 1
    assert r['azure'] == 'subida_y_lectura_verificadas'
    antes = copy.deepcopy(lago.archivos)
    capturar([benchmark()], 'blender-open-data', tmp_path, lago=lago)
    assert lago.archivos == antes
    assert len(lago.archivos) == 2


def test_zip_licencia_y_esquema(tmp_path):
    archivo = tmp_path / 'snapshot.zip'
    with zipfile.ZipFile(archivo, 'w') as z:
        z.writestr('LICENSE.txt', 'CC0')
        z.writestr('data.jsonl', json.dumps(benchmark()) + '\n')
    assert len(list(registros_zip(archivo))) == 1
    with zipfile.ZipFile(archivo, 'w') as z:
        z.writestr('data.jsonl', '{}')
    with pytest.raises(ValueError): list(registros_zip(archivo))


def test_sin_datos_no_publica(tmp_path):
    with pytest.raises(ValueError): capturar([{}], 'sonda', tmp_path)


def test_conserva_nivel_y_gpu_para_geoda_sin_datos_personales():
    d = medicion()
    d['equipo'] = {'cpu': 'prueba', 'nivel': 'N2', 'nivel_estimado': True, 'huella': 'abc',
                   'gpu_vista': {'modelo': 'Intel UHD 620', 'version': '4.6'}, 'so_version': '6.1',
                   'gpu_cycles': [], 'usuario': 'no-debe-pasar'}
    equipo = sonda(d)[0]['equipo']
    assert equipo['nivel'] == 'N2' and equipo['gpu_vista']['modelo'] == 'Intel UHD 620'
    assert 'usuario' not in equipo and 'so_version' not in equipo


def test_recolector_tres_fuentes_y_reintento_del_buzon(tmp_path):
    from g7b_ingesta import catalogo
    from g7b_lago.memoria import LagoMemoria
    from g7b_telemetria.recopilar import recopilar

    cat = catalogo.cargar()
    funciones = catalogo.por_id(cat)["caniuse-web3d"]["sensor"]["solo_ids"]
    matriz = tmp_path / "caniuse.json"
    matriz.write_text(json.dumps({"data": {f: {"title": f, "stats": {"chrome": {"100": "a #1"}}}
                                          for f in funciones}}))
    archivo = tmp_path / "blender.zip"
    with zipfile.ZipFile(archivo, "w") as z:
        z.writestr("LICENSE.txt", "CC0")
        z.writestr("data.jsonl", json.dumps(benchmark()))
    lago = LagoMemoria()
    entrada = "bronce/sonda/2026-11-19/medida.json"
    medida = dict(medicion(), entorno="equipo_voluntario")
    lago.escribir_json(entrada, medida)
    salida = tmp_path / "captura"
    informe = recopilar(cat, salida, 5, snapshot=archivo, caniuse=matriz, lago=lago)
    assert informe["conteos"] == {"recibida": 3, "pendiente": 7, "en_espera": 1}
    observadas = list((salida / "sonda-g7b").rglob("mediciones.jsonl"))
    assert json.loads(observadas[0].read_text())["entorno"] == "equipo_voluntario"
    matriz_local = (salida / "caniuse-web3d/compatibilidad.jsonl").read_text().splitlines()
    assert len(matriz_local) == len(funciones)
    assert all(json.loads(r)["codigo"] == "a #1" for r in matriz_local)
    plata = lago.listar("plata/")
    assert len(plata) == 3
    repetido = recopilar(cat, salida, 5, snapshot=archivo, caniuse=matriz, lago=lago)
    assert repetido["conteos"] == {"sin_novedad": 3, "pendiente": 7, "en_espera": 1}
    assert lago.listar("plata/") == plata


def test_recolector_continua_tras_dato_invalido_y_matriz_incompleta(tmp_path):
    from g7b_ingesta import catalogo
    from g7b_telemetria.recopilar import recopilar

    carpeta = tmp_path / "sondas"
    carpeta.mkdir()
    (carpeta / "a.json").write_text("no-json")
    (carpeta / "b.json").write_text(json.dumps(medicion()))
    matriz = tmp_path / "matriz.json"
    matriz.write_text('{"data": {}}')
    informe = recopilar(catalogo.cargar(), tmp_path / "salida", carpeta=carpeta, caniuse=matriz,
                        solo=["sonda-g7b", "caniuse-web3d"])
    assert informe["conteos"] == {"parcial": 1, "error": 1, "omitida": 2, "pendiente": 7}
    sonda = next(f for f in informe["fuentes"] if f["fuente"] == "sonda-g7b")
    assert sonda["informe"]["conteos"]["rechazados"] == 1
    assert sonda["informe"]["conteos"]["aceptado"] == 1


def test_el_buzon_reintenta_despues_de_una_escritura_parcial(tmp_path, monkeypatch):
    from g7b_ingesta import catalogo
    from g7b_lago.memoria import LagoMemoria
    from g7b_telemetria.recopilar import recopilar

    lago = LagoMemoria()
    lago.escribir_json("bronce/sonda/2026-11-19/m.json", medicion())
    original = lago.leer_jsonl_gz

    def lectura(ruta):
        if ruta.startswith("plata/"):
            raise OSError("fallo temporal")
        return original(ruta)

    monkeypatch.setattr(lago, "leer_jsonl_gz", lectura)
    def ejecutar():
        return recopilar(catalogo.cargar(), tmp_path, lago=lago, solo=["sonda-g7b"])
    assert ejecutar()["conteos"]["error"] == 1
    assert not lago.listar("control/telemetria/recibos_sonda/")
    monkeypatch.setattr(lago, "leer_jsonl_gz", original)
    assert ejecutar()["conteos"]["recibida"] == 1
    assert len(lago.listar("control/telemetria/recibos_sonda/")) == 1


def test_sonda_aframe_recalcula_metricas_y_rechaza_campos_ajenos(tmp_path):
    from g7b_ingesta import catalogo
    from g7b_lago.memoria import LagoMemoria
    from g7b_telemetria.aframe import resumir
    from g7b_telemetria.recopilar import recopilar

    dato = {"contrato": "amatista.sonda_aframe/1", "fecha": "2026-11-19T00:00:00Z",
            "version": "1.7.0", "entorno": "laboratorio", "carga": "practica",
            "intervalos_ms": [10] * 180 + [30] * 100, "max_llamadas": 4, "max_triangulos": 100}
    fila = resumir(dato)
    assert fila["fps_observados"] == pytest.approx(280000 / 4800)
    assert fila["p95_ms"] == 30 and fila["p50_ms"] == 10
    for cambio in ({"url": "privado"}, {"intervalos_ms": [float("nan")]},
                   {"max_triangulos": True}, {"entorno": "sin_clasificar"}):
        with pytest.raises(ValueError):
            resumir(dict(dato, **cambio))
    entrada = tmp_path / "aframe.json"
    entrada.write_text(json.dumps(dato))
    lago = LagoMemoria()
    for _ in range(2):
        informe = recopilar(catalogo.cargar(), tmp_path / "captura", lago=lago, solo=["sonda-aframe"],
                            entrada_aframe=entrada)
        assert informe["conteos"]["recibida"] == 1
    assert len(lago.listar("plata/telemetria_web/")) == 1
    assert not lago.listar("plata/telemetria/")


def test_snapshot_incompatible_y_carpeta_vacia_no_son_datos_al_dia(tmp_path):
    from g7b_ingesta import catalogo
    from g7b_telemetria.capturar import seleccionar_opendata
    from g7b_telemetria.recopilar import recopilar

    with pytest.raises(ValueError, match="registros v4"):
        seleccionar_opendata([{"schema_version": "v5"}])
    resultado = recopilar(catalogo.cargar(), tmp_path / "captura", carpeta=tmp_path, solo=["sonda-g7b"])
    assert resultado["conteos"]["sin_entrada"] == 1


@pytest.mark.parametrize("entorno,consiente,esperada", [
    ("github_actions", True, "relativa"), ("ci", True, "relativa"), ("nube", True, "relativa"),
    ("equipo_voluntario", True, "relativa"), ("laboratorio", True, "relativa"),
    ("no_declarado", True, "relativa"), ("equipo_estudiante", True, "directa"),
    ("laboratorio_escolar", False, "relativa"), ("laboratorio_escolar", True, "directa"),
    ("equipo_estudiante", "true", "relativa"),
])
def test_procedencia_de_la_sonda_se_conserva_hasta_el_cubo(entorno, consiente, esperada):
    from g7b_almacen.cubo import clase_de

    medida = sonda(dict(medicion(), entorno=entorno, consentimiento=consiente))[0]
    assert medida["entorno"] == entorno
    assert clase_de(medida)[0] == esperada


def test_entorno_ausente_y_entorno_desconocido():
    from g7b_almacen.cubo import clase_de

    assert clase_de(sonda(medicion())[0])[0] == "relativa"
    with pytest.raises(ValueError, match="entorno"):
        sonda(dict(medicion(), entorno="inesperado"))
