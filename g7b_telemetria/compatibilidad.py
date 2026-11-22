"""Compatibilidad declarada por Can I Use, con sus notas y versión de navegador."""
from datetime import datetime, timezone
from pathlib import Path

from g7b_ingesta import red
from g7b_ingesta.sensores import sensor_json_api
from .capturar import canon, huella


def capturar(fuente, lago, salida, limite, entrada=None, simulacro=False):
    """Una matriz completa en cada revisión. 'limite' aplica a benchmarks, no a celdas."""
    leer = red.obtener
    if entrada is not None:
        cuerpo = Path(entrada).read_bytes()
        def leer(url, cabeceras):
            return red.Respuesta(200, {}, cuerpo)

    resultado, _ = sensor_json_api(fuente, {}, leer)
    crudos = sorted(resultado["registros"], key=lambda r: r["id"])
    if {r["id"] for r in crudos} != set(fuente["sensor"]["solo_ids"]):
        raise ValueError("faltan funciones configuradas en Can I Use")
    filas = []
    for r in crudos:
        stats = r["datos"]["stats"]
        if not isinstance(stats, dict) or not stats:
            raise ValueError("matriz sin navegadores")
        for navegador, versiones in sorted(stats.items()):
            if not isinstance(versiones, dict) or not versiones:
                raise ValueError("navegador sin versiones")
            for version, codigo in sorted(versiones.items()):
                if not isinstance(codigo, str) or not codigo.strip():
                    raise ValueError("celda sin código")
                filas.append({"contrato": "amatista.compatibilidad_web/1", "fuente": fuente["id"],
                              "funcion": r["id"], "navegador": navegador, "version": version,
                              "codigo": codigo, "soporte": codigo.split()[0],
                              "url": r["url"], "licencia": fuente["licencia"]})
    lote = huella(crudos)
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "compatibilidad.jsonl").write_bytes(b"\n".join(map(canon, filas)) + b"\n")
    resumen = {"fuente": fuente["id"], "lote": lote, "funciones": len(crudos), "celdas": len(filas),
               "azure": "no_solicitado", "url": fuente["sensor"]["url"],
               "extraido_en": datetime.now(timezone.utc).isoformat()}
    if lago is not None and not simulacro:
        for ruta, registros in [(f"bronce/telemetria/{fuente['id']}/{lote}.jsonl.gz", crudos),
                                (f"plata/compatibilidad/{fuente['id']}/{lote}.jsonl.gz", filas)]:
            lago.subir_jsonl_gz(ruta, registros)
            if huella(lago.leer_jsonl_gz(ruta)) != huella(registros):
                raise RuntimeError("falló la verificación de la matriz de compatibilidad")
        estado = f"control/telemetria/{fuente['id']}.json"
        previo = lago.leer_json(estado, por_omision={}) or {}
        resumen.update(nada_nuevo=previo.get("lote") == lote, azure="subida_y_lectura_verificadas")
        lago.escribir_json(estado, {"lote": lote, "ultima_captura": resumen["extraido_en"]})
    (salida / "informe.json").write_bytes(canon(resumen))
    return resumen
