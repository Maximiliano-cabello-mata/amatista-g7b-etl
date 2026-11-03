# G7B

**El motor de datos del 3D libre.** G7B mide cómo corre el software 3D libre en computadoras reales, de las más viejas a las más potentes, y reúne lo que se sabe de él: documentación, técnicas, texturas y herramientas. Con eso decide cómo debe trabajar cada equipo. Cada dato lleva su fuente, su versión y su licencia.

Es el proyecto hermano de **[Amatista](https://github.com/Maximiliano-cabello-mata/amatista)**, la plataforma que enseña 3D con Blender y A-Frame.
- **Separados:** cada uno tiene su repo y sus nubes.
- **Unidos por contratos JSON:** G7B mide y decide; Amatista enseña, recomienda y es la única que guarda datos de personas.

```text
  internet ──► Geodar Radar ──► Azure (lago) ──► embudo ──► MongoDB (documentos y catálogos)
  equipos  ──► sonda ──────────► Azure (lago) ──► cubo DuckDB ──► Geoda ──► perfiles.json ──► Amatista
```

## Hack4Edu

Este repo participa en **Hack4Edu** junto con Amatista. La etiqueta de Git **`hack4edu`** marca el corte: lo anterior es lo que ya teníamos; lo posterior, lo trabajado en estos días. Evidencia y comandos para comprobarlo: **[docs/hack4edu/](docs/hack4edu/README.md)**.

```bash
git log --oneline hack4edu..main      # lo trabajado durante Hack4Edu
```

## Las piezas

| Pieza | Qué hace | Carpeta | Estado |
|---|---|---|---|
| **Geodar Radar** | Vigila 31 fuentes de 3D en internet (foros, manuales, artículos, texturas CC0, herramientas libres, telemetría web) y enruta cada dato a su destino | `geodar/`, `g7b_ingesta/`, `fuentes/` | ✅ Pruebas en verde; probar en vivo con Actions antes de encender |
| **Arañas** | El manual de Blender en 4 versiones y manuales Sphinx, en Zyte | `motor_extraccion/` | ✅ En producción: 987 documentos publicados |
| **Lago** | Azure Blob: bronce (crudo) → plata → oro | `g7b_lago/`, `infra/azure/` | ✅ En producción |
| **Embudo** | 5 etapas de calidad antes de MongoDB, con motivos | `g7b_ingesta/` | ✅ En producción |
| **Sonda** | Mide Blender (vista 3D, edición, animación, render) en cualquier equipo | `sonda/` | ✅ v0.2 |
| **Telemetría** | Sonda y Blender Open Data con controles numéricos → Azure | `g7b_telemetria/` | ✅ Verificada en Azure el 3-nov |
| **Cubo** | Parquet + DuckDB versionado, seis dimensiones | `g7b_almacen/` | ✅ 3,003 mediciones, verificado en Azure |
| **Geoda** | El kernel: nivel del equipo (N0–N4), perfiles con evidencia, costos y plan reversible | `geoda/` | 🟡 Cimientos (0.1.0) |
| **Azure privado** | Jobs con identidad administrada, OIDC y catálogo de ofertas | `infra/azure/`, `infra/ofertas/` | 🟡 Laboratorio desplegado |
| **Análisis** | Cuadernos de Deepnote (cubo y calidad documental) | `analisis/` | ✅ |

## Probarlo

```bash
pip install -r requirements-dev.txt          # incluye lo del lago, el cubo y las pruebas
python -m pytest pruebas -q                  # 112 pruebas; 9 más con Azurite (AZURE_PRUEBAS_CONEXION)
python -m geodar mapa                        # dónde están los sensores
python -m geoda perfiles                     # perfiles por nivel (sin cubo: reglas base)
python -m geoda decidir --huella equipo.json # el plan para un equipo
```

## Documentos

El índice completo, ordenado, está en **[docs/README.md](docs/README.md)**. Los de entrada:
- [Visión](docs/VISION.md): el norte, y cómo se unen Amatista, G7B y Geoda.
- [Plan maestro](docs/PLAN_MAESTRO.md): el camino a seguir. Manda sobre los demás planes.
- [Geoda](docs/GEODA.md): cómo está estructurado el kernel y qué ya existe.
- [Geodar Radar](docs/GEODAR_RADAR.md) y su [mapa de sensores](docs/GEODAR_RADAR_MAPA.md).
- [Telemetría](docs/TELEMETRIA.md) y [cubo](docs/CUBO.md): lo verificado en Azure.
- [CHANGELOG](CHANGELOG.md): qué cambió y cuándo, antes y durante Hack4Edu.

## Licencias

El código que usa la API de Blender es GPL-3.0 o posterior; para el resto de G7B se propone AGPL-3.0. Para los datos publicados se propone CC BY 4.0 o CC0, con DOI. «Blender» es una marca de la Blender Foundation.
