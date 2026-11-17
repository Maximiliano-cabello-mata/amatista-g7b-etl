"""Geodar Radar: una sola orden para los sensores de 3D en internet.

    python -m geodar mapa                         dónde están los sensores, qué miden y a dónde va cada cosa
    python -m geodar mapa --markdown docs/GEODAR_RADAR_MAPA.md
    python -m geodar mapa --estado                + última revisión y errores (necesita AZURE_LAGO_URL)
    python -m geodar probar --fuente blender-artists     revisa una fuente en vivo, SIN escribir nada
    python -m geodar probar --todas                       todas, incluidas las inactivas (para decidir)
    python -m geodar licencias                    lo que falta confirmar antes de activar una fuente
    python -m geodar vigilar [--fuente ID] [--forzar] [--simulacro]    la vigilancia real (a bronce)
    python -m geodar procesar | publicar | catalogar | senales [--simulacro]
    python -m geodar telemetria [--colector blender_open_data] [--limite 20000] [--simulacro]
                                                  el radar de telemetría (cifras de equipos, a bronce y plata)
    python -m geodar salud                        ¿algún sensor falla o se atrasó? (sale con 1 si sí)

Quién hace qué (docs/GEODAR_RADAR.md, sección 1):
    radar de telemetría       cifras de equipos y rendimiento, con el estándar g7b.hardware/1 → cubo
    arañas de Zyte            documentación (manuales, notas de versión) → embudo → MongoDB
    sensores directos         feeds, APIs y foros → bronce

El ciclo completo, sin intervención: vigilar → (Zyte al lago) → procesar → publicar → catalogar → senales;
y una vez por semana, telemetria → cubo → Geoda.
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

from g7b_ingesta import catalogo as cat
from g7b_ingesta import red
from g7b_ingesta.sensores import SENSORES

ESTADO = "control/sensores.json"
SALUD = "control/geodar_salud.json"
ICONO_ESTADO = {"activa": "✅ activa", "inactiva": "⏸️ inactiva", "licencia": "🔒 licencia por confirmar",
                "externa": "🔗 la trae otra tarea"}


def estado_de(fuente):
    if not fuente["licencia_verificada"]:
        return "licencia"
    if not fuente["activa"]:
        return "inactiva"
    if fuente["extractor"] == "externo":
        return "externa"
    if fuente["extractor"] == "telemetria" and fuente.get("colector") == "pendiente":
        return "inactiva"
    return "activa"


def herramienta(fuente):
    """Qué parte de Geodar se encarga de la fuente: la separación de responsabilidades."""
    if fuente["extractor"] == "telemetria" or (cat.destino(fuente) == "telemetria"
                                                and fuente["extractor"] == "directo"):
        return "radar de telemetría"
    if fuente["extractor"] == "zyte":
        return "araña de documentación (Zyte)"
    if fuente["extractor"] == "externo":
        return "gestor externo"
    if fuente["extractor"] == "descarga":
        return "descarga directa"
    return "sensor directo"


def donde(fuente):
    s = fuente["sensor"]
    if s.get("tipo") == "github_releases":
        return f"GitHub: {len(s.get('repos', []))} repos"
    if s.get("tipo") == "stackexchange":
        return f"{s.get('sitio')}.stackexchange.com"
    if s.get("tipo") == "discourse":
        return s.get("base", "").replace("https://", "")
    if fuente["extractor"] == "externo":
        return fuente.get("gestor", "")
    if fuente["extractor"] == "telemetria":
        return f"colector {fuente.get('colector')}: " + ", ".join(fuente.get("dominios") or [])
    return ", ".join(fuente.get("dominios") or []) or s.get("url", "")


# ---------------------------------------------------------------- mapa

def mapa(catalogo, estados=None):
    filas = []
    for f in catalogo["fuentes"]:
        e = (estados or {}).get(f["id"], {})
        filas.append({
            "familia": cat.familia(f), "id": f["id"], "nombre": f["nombre"], "donde": donde(f),
            "sensor": f["sensor"]["tipo"], "extractor": f["extractor"], "destino": cat.destino(f),
            "herramienta": herramienta(f),
            "licencia": f["licencia"], "modo": f["modo"], "estado": estado_de(f),
            "cada_horas": f["frecuencia_horas"],
            "ultima_revision": e.get("ultima_revision"), "ultimo_error": e.get("ultimo_error"),
        })
    return filas


def mapa_markdown(catalogo, estados=None, hoy=None):
    filas = mapa(catalogo, estados)
    hoy = hoy or datetime.now(timezone.utc).date().isoformat()
    cuenta = Counter(f["estado"] for f in filas)
    lineas = [
        "# Geodar Radar: mapa de sensores",
        "",
        f"Generado con `python -m geodar mapa --markdown` el {hoy}, desde [`fuentes/catalogo.yml`](../fuentes/catalogo.yml). "
        "No se edita a mano: se cambia el catálogo y se vuelve a generar. Cómo funciona: [GEODAR_RADAR.md](GEODAR_RADAR.md).",
        "",
        f"**{len(filas)} fuentes:** " + ", ".join(f"{n} {ICONO_ESTADO[k]}" for k, n in cuenta.most_common()) + ".",
        "",
        "## Quién hace qué",
        "",
        "| Herramienta | Responsabilidad | Fuentes |",
        "|---|---|---|",
    ]
    por_herramienta = Counter(f["herramienta"] for f in filas)
    responsabilidad = {
        "radar de telemetría": "Cifras de equipos y rendimiento, con el estándar `g7b.hardware/1` → cubo (`geodar telemetria`)",
        "araña de documentación (Zyte)": "Documentación: manuales y notas de versión → embudo → MongoDB",
        "sensor directo": "Feeds, APIs y foros: el sensor ya trae el dato → bronce (`geodar vigilar`)",
        "descarga directa": "Archivos (PDF) → bronce",
        "gestor externo": "Lo trae otra tarea (la sonda, Amatista)",
    }
    lineas += [f"| {h} | {responsabilidad[h]} | {por_herramienta.get(h, 0)} |" for h in responsabilidad]
    lineas += [
        "",
        "## A dónde va cada cosa",
        "",
        "Todo entra primero crudo a Azure (`bronce/<fuente>/<fecha>/`), así nada se pierde. Después:",
        "",
        "| Destino | Va a |",
        "|---|---|",
    ]
    lineas += [f"| `{k}` | {v} |" for k, v in cat.DESTINOS.items()]
    con_estado = estados is not None
    for clave, nombre in cat.FAMILIAS.items():
        de_familia = [f for f in filas if f["familia"] == clave]
        if not de_familia:
            continue
        lineas += ["", f"## {clave} · {nombre}", ""]
        cabecera = "| Fuente | Dónde está el sensor | Herramienta | Sensor | Destino | Licencia | Estado | Cada |"
        if con_estado:
            cabecera += " Última revisión | Último error |"
        lineas += [cabecera, "|" + "---|" * (cabecera.count("|") - 1)]
        for f in de_familia:
            fila = (f"| **{f['id']}**<br>{f['nombre']} | {f['donde']} | {f['herramienta']} | `{f['sensor']}` | "
                    f"`{f['destino']}` | {f['licencia']} ({f['modo']}) | {ICONO_ESTADO[f['estado']]} | {f['cada_horas']} h |")
            if con_estado:
                fila += f" {f['ultima_revision'] or '—'} | {(f['ultimo_error'] or '—')[:80]} |"
            lineas.append(fila)
    return "\n".join(lineas) + "\n"


# ---------------------------------------------------------------- probar

def probar(catalogo, ids=None, obtener=red.obtener, muestras=3, salida=print):
    """Corre el sensor en vivo con estado vacío. No escribe nada en ningún lado."""
    resultados = []
    for f in catalogo["fuentes"]:
        if ids and f["id"] not in ids:
            continue
        if f["sensor"]["tipo"] not in SENSORES:  # externo
            continue
        r = {"fuente": f["id"], "estado": estado_de(f)}
        try:
            out, _ = SENSORES[f["sensor"]["tipo"]](f, {}, obtener)
            r.update({"ok": True, "nota": out["nota"], "registros": len(out["registros"]), "urls": len(out["urls"]),
                      "ejemplos": [{"titulo": x.get("titulo"), "url": x.get("url")} for x in out["registros"][:muestras]]
                      or out["urls"][:muestras]})
        except Exception as error:
            r.update({"ok": False, "error": f"{type(error).__name__}: {str(error)[:200]}"})
        resultados.append(r)
        salida(json.dumps(r, ensure_ascii=False))
    return resultados


# ---------------------------------------------------------------- salud

def salud(catalogo, estados, ahora=None, telemetria=None):
    """Por cada fuente vigilable: ok, nunca revisada, atrasada (más del doble de su frecuencia) o con error.

    telemetria = {id: estado del radar} para las fuentes del radar de telemetría (su «ultima_captura»).
    """
    ahora = ahora or datetime.now(timezone.utc)
    informe = []
    telemetria = telemetria or {}
    fuentes = cat.vigilables(catalogo) + cat.de_telemetria(catalogo)
    for f in fuentes:
        if f["extractor"] == "telemetria":
            t = telemetria.get(f["id"], {})
            e = {"ultima_revision": t.get("ultima_captura"), "ultimo_error": t.get("ultimo_error")}
        else:
            e = estados.get(f["id"], {})
        ultima = e.get("ultima_revision")
        if e.get("ultimo_error"):
            veredicto = "error"
        elif not ultima:
            veredicto = "nunca_revisada"
        elif ahora - datetime.fromisoformat(ultima) > timedelta(hours=2 * f["frecuencia_horas"]):
            veredicto = "atrasada"
        else:
            veredicto = "ok"
        informe.append({"fuente": f["id"], "veredicto": veredicto, "ultima_revision": ultima,
                        "ultimo_error": e.get("ultimo_error")})
    return informe


# ---------------------------------------------------------------- radar de telemetría

def estado_telemetria(lago, id_fuente):
    return lago.leer_json(f"control/telemetria/{id_fuente}.json", por_omision={}) or {}


def colector_blender_open_data(fuente, lago, salida, limite, entrada=None, simulacro=False):
    """El archivo completo de Blender Open Data, por tandas (g7b_telemetria/capturar.py)."""
    from pathlib import Path

    from g7b_telemetria import capturar as cap

    archivo = Path(entrada) if entrada else Path(salida) / "opendata.zip"
    if not entrada:
        cap.descargar(archivo)
    registros = cap.registros_zip(archivo)
    if simulacro:
        seleccion, nuevo, conteos = cap.seleccionar_opendata(registros, {}, limite)
        informe = cap.capturar(seleccion, "blender-open-data", Path(salida), len(seleccion)) if seleccion else {}
        return {**informe, "seleccion": dict(conteos), "simulacro": True}
    return cap.capturar_incremental(registros, lago, salida, limite)


COLECTORES = {"blender_open_data": colector_blender_open_data}


def telemetria(catalogo, lago, salida="captura/telemetria", limite=20000, solo=None, entrada=None,
               simulacro=False, imprimir=print):
    """Corre el radar de telemetría. Una fuente rota no detiene a las demás; su error queda en el lago."""
    import os

    resultados = []
    for f in cat.de_telemetria(catalogo):
        if solo and f["colector"] != solo and f["id"] != solo:
            continue
        r = {"fuente": f["id"], "colector": f["colector"]}
        try:
            r["informe"] = COLECTORES[f["colector"]](f, lago, os.path.join(salida, f["id"]), limite,
                                                    entrada=entrada, simulacro=simulacro)
            r["ok"] = True
        except Exception as error:  # una fuente rota no detiene a las demás
            r.update(ok=False, error=f"{type(error).__name__}: {str(error)[:200]}")
            if lago is not None and not simulacro:
                estado = estado_telemetria(lago, f["id"])
                estado.update(ultimo_error=r["error"],
                              ultimo_error_en=datetime.now(timezone.utc).isoformat(timespec="seconds"))
                lago.escribir_json(f"control/telemetria/{f['id']}.json", estado)
        resultados.append(r)
        imprimir(json.dumps(r, ensure_ascii=False))
    return resultados


# ---------------------------------------------------------------- orden

def _lago():
    from g7b_lago import Lago

    return Lago.desde_entorno()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Órdenes que ya existen en g7b_ingesta: se pasan tal cual, con sus propias opciones.
    delegadas = {"vigilar": "g7b_ingesta.vigilar", "procesar": "g7b_ingesta.procesar",
                 "publicar": "g7b_ingesta.publicar", "catalogar": "g7b_ingesta.catalogar",
                 "senales": "g7b_ingesta.senales"}
    if argv and argv[0] in delegadas:
        import importlib

        importlib.import_module(delegadas[argv[0]]).main(argv[1:])  # sus fallas salen con sys.exit
        return 0

    p = argparse.ArgumentParser(prog="geodar", description="Geodar Radar: sensores de 3D en internet.",
                                epilog="También: vigilar, procesar, publicar, catalogar, senales (ver --help de cada una).")
    sub = p.add_subparsers(dest="orden", required=True)
    m = sub.add_parser("mapa", help="dónde están los sensores y a dónde va cada cosa")
    m.add_argument("--markdown", help="escribir el mapa en este archivo .md")
    m.add_argument("--estado", action="store_true", help="agregar última revisión y errores (lee el lago)")
    m.add_argument("--json", action="store_true")
    pr = sub.add_parser("probar", help="revisar fuentes en vivo sin escribir nada")
    grupo = pr.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--fuente", action="append", help="id del catálogo (se puede repetir)")
    grupo.add_argument("--todas", action="store_true")
    pr.add_argument("--muestras", type=int, default=3)
    sub.add_parser("licencias", help="lo pendiente de confirmar antes de activar")
    t = sub.add_parser("telemetria", help="radar de telemetría: cifras de equipos y rendimiento")
    t.add_argument("--colector", help="solo este colector o fuente (p. ej. blender_open_data)")
    t.add_argument("--limite", type=int, default=20000, help="registros por fuente en esta tanda")
    t.add_argument("--salida", default="captura/telemetria")
    t.add_argument("--entrada", help="archivo ya descargado (ZIP de Open Data), para pruebas")
    t.add_argument("--simulacro", action="store_true", help="sin leer ni escribir el lago")
    s = sub.add_parser("salud", help="sensores con error o atrasados")
    s.add_argument("--guardar", action="store_true", help=f"escribir el informe en {SALUD}")
    o = p.parse_args(argv)

    catalogo = cat.cargar()
    if o.orden == "mapa":
        estados = _lago().leer_json(ESTADO, por_omision={}) if o.estado else None
        if o.json:
            print(json.dumps(mapa(catalogo, estados), ensure_ascii=False, indent=2))
        elif o.markdown:
            with open(o.markdown, "w", encoding="utf-8") as archivo:
                archivo.write(mapa_markdown(catalogo, estados))
            print(f"Mapa escrito en {o.markdown}")
        else:
            for f in mapa(catalogo, estados):
                print(f"{f['familia']}  {ICONO_ESTADO[f['estado']]:<26} {f['id']:<32} {f['sensor']:<16} → "
                      f"{f['destino']:<11} {f['donde']}")
        return 0
    if o.orden == "probar":
        resultados = probar(catalogo, None if o.todas else set(o.fuente), muestras=o.muestras)
        malos = [r["fuente"] for r in resultados if not r["ok"]]
        print(f"\n{len(resultados) - len(malos)} de {len(resultados)} fuentes respondieron."
              + (f" Con error: {', '.join(malos)}" if malos else ""))
        return 1 if malos else 0
    if o.orden == "licencias":
        for f in catalogo["fuentes"]:
            if not f["licencia_verificada"] or f.get("revisar") or f.get("condiciones"):
                print(f"- {f['id']} ({f['licencia']}, {'verificada' if f['licencia_verificada'] else 'POR CONFIRMAR'})")
                for campo in ("revisar", "condiciones"):
                    if f.get(campo):
                        print(f"    {campo}: {' '.join(str(f[campo]).split())}")
        return 0
    if o.orden == "telemetria":
        lago = None if o.simulacro else _lago()
        resultados = telemetria(catalogo, lago, o.salida, o.limite, o.colector, o.entrada, o.simulacro)
        malos = [r["fuente"] for r in resultados if not r["ok"]]
        print(f"\n{len(resultados) - len(malos)} de {len(resultados)} fuentes de telemetría capturadas."
              + (f" Con error: {', '.join(malos)}" if malos else ""))
        return 1 if malos or not resultados else 0
    if o.orden == "salud":
        lago = _lago()
        de_radar = {f["id"]: estado_telemetria(lago, f["id"]) for f in cat.de_telemetria(catalogo)}
        informe = salud(catalogo, lago.leer_json(ESTADO, por_omision={}) or {}, telemetria=de_radar)
        for fila in informe:
            print(json.dumps(fila, ensure_ascii=False))
        malos = [f for f in informe if f["veredicto"] in ("error", "atrasada")]
        if o.guardar:
            lago.escribir_json(SALUD, {"cuando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                       "fuentes": informe})
        print(f"\n{len(informe) - len(malos)} de {len(informe)} sensores al día.")
        return 1 if malos else 0
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
