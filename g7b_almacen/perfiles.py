"""perfiles.json v0 (contrato ``g7b.perfil/1``): qué ajustes usar en cada nivel de equipo.

La regla es la del plan (sección 0, punto 4, en su versión sin LPIPS todavía): por cada nivel y
versión de Blender, el perfil **más completo** que sigue siendo fluido.

- Fluido = la mediana de los cuadros por segundo de la vista 3D llega a 30. Si ese nivel no tiene
  mediciones con ventana, se usa la animación (24 cuadros por segundo) y el perfil lo dice.
- Solo cuentan las pruebas con calidad ``ok`` (repetidas y estables) de mediciones reales.
- Un perfil es ``confiable`` con 5 mediciones o más de 3 equipos o más (horizonte H1); si no,
  ``provisional``. Amatista puede usar los provisionales, pero debe mostrarlos como tales.

Los ajustes de cada perfil son los mismos que usa la sonda (``sonda/g7b_sonda.py``, PERFILES);
una prueba comprueba que no se separen.
"""
from datetime import datetime, timezone

CONTRATO = "g7b.perfil/1"

AJUSTES = {
    "minimo": {"subsurf": 0, "simplify": True, "muestras": 4, "res_pct": 50},
    "ligero": {"subsurf": 1, "simplify": False, "muestras": 16, "res_pct": 75},
    "completo": {"subsurf": 2, "simplify": False, "muestras": 64, "res_pct": 100},
}
ORDEN = ("completo", "ligero", "minimo")  # del más completo al más ligero
CRITERIOS = {
    "vista3d": {"prueba": "vista3d", "fps_min": 30.0},
    "animacion": {"prueba": "animacion", "fps_min": 24.0},
}
MIN_MEDICIONES, MIN_EQUIPOS = 5, 3


def _celdas(con):
    """Mediana de fps por nivel, versión, criterio y perfil, con su evidencia."""
    filas = con.execute("""
        SELECT d.nivel, v.version_corta, h.prueba, h.perfil,
               median(h.mediana) AS fps, count(*) AS mediciones, count(DISTINCT h.clave_dispositivo) AS equipos
        FROM hechos_medicion h
        JOIN dim_dispositivo d USING (clave_dispositivo)
        JOIN dim_version v USING (clave_version)
        WHERE h.calidad = 'ok' AND h.origen <> 'sintetico' AND h.unidad = 'fps'
          AND h.prueba IN ('vista3d', 'animacion') AND h.perfil <> '' AND d.nivel <> ''
        GROUP BY ALL
    """).fetchall()
    celdas = {}
    for nivel, version, prueba, perfil, fps, mediciones, equipos in filas:
        celdas[(nivel, version, prueba, perfil)] = {"fps": round(fps, 2), "mediciones": mediciones,
                                                     "equipos": equipos}
    return celdas


def generar(con, ahora=None):
    celdas = _celdas(con)
    perfiles = []
    for nivel, version in sorted({(n, v) for n, v, _p, _f in celdas}):
        criterio = "vista3d" if any((nivel, version, "vista3d", p) in celdas for p in ORDEN) else "animacion"
        regla = CRITERIOS[criterio]
        elegido, celda = None, None
        for perfil in ORDEN:
            c = celdas.get((nivel, version, regla["prueba"], perfil))
            if c and c["fps"] >= regla["fps_min"]:
                elegido, celda = perfil, c
                break
        nota = None
        if elegido is None:
            # Ni el mínimo llega: se recomienda el mínimo y se avisa (o no hay datos de ese criterio).
            elegido = "minimo"
            celda = celdas.get((nivel, version, regla["prueba"], "minimo"))
            nota = "ni el perfil mínimo es fluido" if celda else "sin mediciones del perfil mínimo"
        evidencia = celda or {"fps": None, "mediciones": 0, "equipos": 0}
        confiable = evidencia["mediciones"] >= MIN_MEDICIONES and evidencia["equipos"] >= MIN_EQUIPOS
        perfil = {
            "nivel": nivel,
            "blender": version,
            "perfil": elegido,
            "ajustes": AJUSTES[elegido],
            "criterio": criterio,
            "fps_esperados": evidencia["fps"],
            "fps_min": regla["fps_min"],
            "evidencia": {"mediciones": evidencia["mediciones"], "equipos": evidencia["equipos"]},
            "estado": "confiable" if confiable else "provisional",
        }
        if nota:
            perfil["nota"] = nota
        perfiles.append(perfil)
    return {
        "contrato": CONTRATO,
        "generado": (ahora or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "regla": "el perfil más completo cuya mediana de fps llega al mínimo del criterio",
        "confiable_si": {"mediciones_min": MIN_MEDICIONES, "equipos_min": MIN_EQUIPOS},
        "licencia": "CC0-1.0",
        "perfiles": perfiles,
    }


def validar(documento):
    """Revisión mínima del contrato, para que Amatista no reciba un archivo roto."""
    errores = []
    if documento.get("contrato") != CONTRATO:
        errores.append("contrato")
    for i, p in enumerate(documento.get("perfiles") or []):
        for campo in ("nivel", "blender", "perfil", "ajustes", "criterio", "evidencia", "estado"):
            if campo not in p:
                errores.append(f"perfiles[{i}].{campo}")
        if p.get("perfil") not in AJUSTES:
            errores.append(f"perfiles[{i}].perfil desconocido")
        if p.get("estado") not in ("confiable", "provisional"):
            errores.append(f"perfiles[{i}].estado")
    return errores
