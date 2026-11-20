"""Compara identidades, calidad y valores comunes sobre los mismos archivos de entrada."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys

ENTRADAS = Path(os.environ["RUNNER_TEMP"]) / "entradas-amatista"
BASE = Path(os.environ["GITHUB_WORKSPACE"]) / "resultados-comparacion/telemetria"


def guardar(ruta, dato):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(dato, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def caniuse_anterior():
    from g7b_ingesta import catalogo, red
    from g7b_ingesta.sensores import sensor_json_api
    fuente = catalogo.por_id(catalogo.cargar())["caniuse-web3d"]
    contenido = (ENTRADAS / "caniuse.json").read_bytes()
    datos, _ = sensor_json_api(fuente, {}, lambda url, cab: red.Respuesta(200, {}, contenido))
    filas = [[r["id"], navegador, version, codigo] for r in datos["registros"]
             for navegador, tabla in r["datos"]["stats"].items() for version, codigo in tabla.items()]
    guardar(BASE / "antes/caniuse-sensor.json", filas)


def jsonl(rutas):
    return [json.loads(linea) for ruta in sorted(rutas) for linea in ruta.read_text().splitlines()]


def comparar():
    antes, despues = BASE / "antes", BASE / "despues"
    salida = {}
    for fuente, subdir in (("sonda-g7b", "sonda"), ("blender-open-data", "radar/blender-open-data")):
        a = jsonl((antes / subdir).rglob("mediciones.jsonl"))
        b = jsonl((despues / fuente).rglob("mediciones.jsonl"))
        x = {f["id"]: f for f in a}
        y = {f["id"]: f for f in b}
        assert x and len(x) == len(a) and len(y) == len(b) and x.keys() == y.keys()
        ignorados = {"entorno"}
        iguales = sum({k: v for k, v in x[i].items() if k not in ignorados}
                      == {k: v for k, v in y[i].items() if k not in ignorados} for i in x)
        salida[fuente] = {"antes": len(a), "despues": len(b), "identicos_sin_entorno": iguales,
                          "con_entorno_antes": sum("entorno" in f for f in a),
                          "con_entorno_despues": sum("entorno" in f for f in b),
                          "calidad": dict(Counter(f["estado"] for f in b))}
        assert iguales == len(a)
    anterior = json.loads((antes / "caniuse-sensor.json").read_text())
    matriz = jsonl([despues / "caniuse-web3d/compatibilidad.jsonl"])
    filas = [[f["funcion"], f["navegador"], f["version"], f["codigo"]] for f in matriz]
    assert anterior and sorted(filas) == sorted(anterior)
    salida["caniuse"] = {"funciones": len({f[0] for f in filas}), "celdas_iguales": len(filas)}
    aframe = jsonl((despues / "sonda-aframe").glob("*.jsonl"))
    assert len(aframe) == 3 and all(f["entorno"] == "github_actions" and f["max_triangulos"] >= 12 for f in aframe)
    salida["aframe"] = [{k: f[k] for k in ("intervalos", "duracion_ms", "p50_ms", "p95_ms", "fps_observados")}
                        for f in aframe]
    informe = json.loads((despues / "informe.json").read_text())
    salida["estados"] = informe["conteos"]
    assert salida["estados"] == {"recibida": 4, "pendiente": 7}
    salida["entradas_sha256"] = {}
    for ruta in sorted(ENTRADAS.rglob("*")):
        if ruta.is_file():
            with ruta.open("rb") as f:
                salida["entradas_sha256"][str(ruta.relative_to(ENTRADAS))] = hashlib.file_digest(f, "sha256").hexdigest()
    guardar(BASE / "comparacion.json", salida)
    print("TELEMETRIA " + json.dumps(salida, ensure_ascii=False))


if __name__ == "__main__":
    if sys.argv[1:] == ["caniuse-anterior"]:
        caniuse_anterior()
    elif sys.argv[1:] == ["comparar"]:
        comparar()
    else:
        raise SystemExit("usa caniuse-anterior o comparar")
