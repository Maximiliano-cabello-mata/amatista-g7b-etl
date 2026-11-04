"""Construye el primer DuckDB de G7B a partir de la medición real en Azure.

Experimento aislado: descarga el JSON verificado desde tmp/pruebas-blender/,
construye bronce → plata (Parquet) → oro (DuckDB) localmente, valida calidad y
sube los artefactos exclusivamente a tmp/pruebas-duckdb/<run>-intento<attempt>/.

No escribe bronce/, plata/, oro/, publicado/ ni control/ en Azure, no toca MongoDB.
"""
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timezone

import duckdb

from g7b_almacen import almacen as alm, calidad, cubo, publicacion
from .lago import Lago

ORIGEN = "tmp/pruebas-blender/41379915232-intento1"
DESTINO = "tmp/pruebas-duckdb"


def _sha(datos):
    return hashlib.sha256(datos).hexdigest()


def _id(valor, nombre):
    valor = str(valor or "")
    if not re.fullmatch(r"[1-9][0-9]{0,18}", valor):
        raise ValueError(f"{nombre}: identificador no válido")
    return valor


def _leer_origen(lago, carpeta=ORIGEN):
    """Lee la medición y valida su SHA-256 contra el manifiesto del primer ensayo."""
    if carpeta != ORIGEN:
        raise ValueError("Para esta prueba solo se permite la medición verificada de Blender")
    entrada = lago.contenedor.download_blob(f"{carpeta}/medicion.json").readall()
    prueba = json.loads(
        lago.contenedor.download_blob(f"{carpeta}/verificacion.json").readall()
    )
    medicion = json.loads(entrada)
    if prueba.get("estado") != "verificado" or prueba.get("archivo") != f"{carpeta}/medicion.json":
        raise ValueError("El manifiesto original no indica una medición verificada")
    if prueba.get("sha256") != _sha(entrada):
        raise ValueError("La medición ha cambiado con respecto a la prueba original")
    if (medicion.get("contrato") != "g7b.medicion/1"
            or medicion.get("sintetico") is not False
            or medicion.get("origen") != "actions"
            or medicion.get("completa") is not True):
        raise ValueError("La medición no cumple el contrato real de G7B")
    if not medicion.get("resultados"):
        raise ValueError("La medición está vacía")
    dia = str(medicion.get("fecha") or "")[:10]
    date.fromisoformat(dia)
    return entrada, medicion, dia


def construir_y_subir(lago, run_id, intento, origen=ORIGEN):
    """Prueba completa, con verificación de contenido descargado desde Azure."""
    run_id = _id(run_id, "run_id")
    intento = _id(intento, "intento")
    raiz = f"{DESTINO}/{run_id}-intento{intento}"
    entrada, medicion, dia = _leer_origen(lago, origen)

    with tempfile.TemporaryDirectory(prefix="g7b_aislado_") as temporal:
        local = alm.Carpeta(temporal)
        local.escribir(f"bronce/sonda/{dia}/medicion.json", entrada, sobrescribir=False)

        print("Construyendo Parquet y DuckDB desde la medición real...", flush=True)
        resumen = cubo.construir(local)
        print("Ejecutando la compuerta de calidad...", flush=True)
        reporte = calidad.evaluar(local)
        if not reporte.get("aprobado"):
            raise ValueError(f"La compuerta rechazó el warehouse: {reporte}")
        publicacion.publicar(local, reporte)

        # Comprobar que DuckDB es un archivo real legible y contiene la medición.
        archivo_db = os.path.join(temporal, "oro", "cubo.duckdb")
        with duckdb.connect(archivo_db, read_only=True) as db:
            hechos = db.execute("SELECT count(*) FROM hechos_medicion").fetchone()[0]
            corridas = db.execute("SELECT count(DISTINCT medicion_id) FROM hechos_medicion").fetchone()[0]
            origenes = db.execute(
                "SELECT DISTINCT origen FROM hechos_medicion"
            ).fetchall()
        if hechos != len(medicion["resultados"]) or corridas != 1 or origenes != [("actions",)]:
            raise ValueError("DuckDB no contiene exactamente la medición esperada")

        perfiles = json.loads(local.leer("oro/perfiles.json"))
        # Una sola máquina todavía no ofrece evidencias para recomendaciones confiables.
        if any(p.get("estado") == "confiable" for p in perfiles.get("perfiles", [])):
            raise ValueError("Una sola computadora no justifica un perfil confiable")

        # Copia la salida a una carpeta temporal de Azure; no toca el lago productivo.
        archivos = sorted(
            ruta for prefijo in ("plata/", "oro/", "publicado/")
            for ruta in local.listar(prefijo)
        )
        enviados = {}
        for ruta in archivos:
            datos = local.leer(ruta)
            remoto = f"{raiz}/{ruta}"
            tipo = ("application/json" if ruta.endswith(".json")
                    else "application/vnd.apache.parquet" if ruta.endswith(".parquet")
                    else "text/csv" if ruta.endswith(".csv")
                    else "application/octet-stream")
            lago.subir_bytes(remoto, datos, tipo=tipo, sobrescribir=False)
            confirmado = lago.contenedor.download_blob(remoto).readall()
            if _sha(confirmado) != _sha(datos):
                raise IOError(f"Error de integridad al descargar {remoto}")
            enviados[ruta] = {"ruta": remoto, "sha256": _sha(datos), "bytes": len(datos)}

        verificacion = {
            "contrato": "g7b.warehouse_aislado/1",
            "estado": "verificado",
            "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "origen_azure": f"{origen}/medicion.json",
            "destino_azure": raiz,
            "blender": medicion.get("blender", {}).get("version"),
            "medicion_origen": medicion.get("origen"),
            "conteos": resumen["conteos"],
            "hechos_medicion": hechos,
            "corridas": corridas,
            "perfiles": perfiles.get("perfiles", []),
            "calidad": {"aprobado": True, "avisos": reporte.get("avisos"),
                        "fallas": reporte.get("fallas")},
            "archivos": enviados,
        }
        contenido = json.dumps(verificacion, ensure_ascii=False, indent=2).encode()
        destino_manifiesto = f"{raiz}/verificacion_duckdb.json"
        lago.subir_bytes(destino_manifiesto, contenido,
                        tipo="application/json", sobrescribir=False)
        if lago.contenedor.download_blob(destino_manifiesto).readall() != contenido:
            raise IOError("No se verificó el manifiesto final de DuckDB")

        print("G7B_DUCKDB_AZURE_VERIFICADO", json.dumps({
            "destino": raiz, "hechos_medicion": hechos,
            "corridas": corridas, "calidad": reporte["aprobado"],
            "archivos": len(enviados) + 1,
            "cubo": enviados["oro/cubo.duckdb"]["ruta"],
            "parquet": enviados["plata/sonda/medicion.parquet"]["ruta"],
        }, ensure_ascii=False), flush=True)
        return verificacion


def main():
    if not os.environ.get("AZURE_LAGO_URL"):
        sys.exit("Falta AZURE_LAGO_URL en el environment amatista1")
    construir_y_subir(
        Lago.desde_entorno(),
        os.environ.get("GITHUB_RUN_ID"),
        os.environ.get("GITHUB_RUN_ATTEMPT"),
    )


if __name__ == "__main__":
    main()
