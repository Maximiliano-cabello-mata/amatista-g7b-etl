"""Ensayo local de los lectores con la misma fila de prueba, fuera del lago."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile


def producir(raiz, carpeta):
    from g7b_almacen.cubo import construir, publicar
    from pruebas.test_cubo import Lago

    fila = json.loads((raiz / "fila.json").read_text())
    informe = construir([("prueba-local", fila)], carpeta / "producto")
    lago = Lago()
    publicar(lago, carpeta / "producto", informe)
    with ZipFile(carpeta / "objetos.zip", "w") as z:
        for nombre, datos in lago.archivos.items():
            z.writestr(nombre, datos)


def leer(raiz, carpeta, productor, lector):
    import duckdb
    from g7b_almacen.descargar import descargar
    from g7b_almacen.geoda_estado import estado_del_cubo
    from pruebas.test_cubo import Lago

    lago = Lago()
    with ZipFile(carpeta / "objetos.zip") as z:
        lago.archivos = {nombre: z.read(nombre) for nombre in z.namelist()}
    destino = raiz / f"{productor}-{lector}.duckdb"
    try:
        mediciones = descargar(lago, destino)["mediciones"]
        assert mediciones == 1
        descarga = "sí"
    except (ValueError, duckdb.CatalogException) as error:
        descarga = "rechazado"
        print(f"{productor} → {lector}, descarga: {error}", file=sys.stderr)
    try:
        estado = estado_del_cubo(lago)
        assert estado["mediciones"] == 1 and estado["recomendaciones_habilitadas"] is False
        agregados = "sí"
    except ValueError as error:
        agregados = "rechazado"
        print(f"{productor} → {lector}, estado: {error}", file=sys.stderr)
    if lector == "corregido" and productor == "pr27":
        from g7b_almacen.paquete_geoda import construir_desde_lago
        try:
            construir_desde_lago(lago, raiz / "sin-clases", verificar_manual=False)
        except ValueError as error:
            assert "carece de clasificación" in str(error)
        else:
            raise AssertionError("se admitió un cubo sin clases para construir el paquete")
    print(json.dumps([descarga, agregados]))


def taller():
    espacio = Path(os.environ["GITHUB_WORKSPACE"])
    productor = {"vigente": espacio / "vigente", "pr26": espacio / "pr26", "pr27": espacio / "pr27"}
    lectores = {**productor, "corregido": espacio / "corregido"}
    script = str(Path(__file__).resolve())
    resumen = ["| Productor | Lector | Descarga verificada | Estado agregado |", "|---|---|---|---|"]
    errores = []
    with tempfile.TemporaryDirectory() as temp:
        raiz = Path(temp)
        # Fixture de pruebas de la v2 canónica, incluidos sus valores y su variación coherente.
        muestra = subprocess.check_output(
            [sys.executable, "-c", "from pruebas.test_cubo import fila; import json; print(json.dumps(fila()))"],
            cwd=productor["pr27"], text=True)
        (raiz / "fila.json").write_text(muestra)
        for nombre, repo in productor.items():
            carpeta = raiz / nombre
            carpeta.mkdir()
            subprocess.run([sys.executable, script, "producir", str(raiz), str(carpeta)],
                           cwd=repo, env={**os.environ, "PYTHONPATH": str(repo)}, check=True)
            for lector, repo_lector in lectores.items():
                salida = subprocess.check_output([sys.executable, script, "leer", str(raiz), str(carpeta), nombre, lector],
                                                 cwd=repo_lector, env={**os.environ, "PYTHONPATH": str(repo_lector)}, text=True)
                descarga, agregado = json.loads(salida.strip().splitlines()[-1])
                resumen.append(f"| {nombre} | {lector} | {descarga} | {agregado} |")
                if (lector == "corregido" or lector == nombre or nombre == "vigente") and (descarga, agregado) != ("sí", "sí"):
                    errores.append(f"{nombre} → {lector}")
    tabla = "\n".join(resumen) + "\n"
    print(tabla)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as salida:
        salida.write(tabla)
    if errores:
        raise SystemExit("Falló una compatibilidad exigida: " + ", ".join(errores))


if __name__ == "__main__":
    if len(sys.argv) == 1:
        taller()
    elif sys.argv[1] == "producir":
        producir(*map(Path, sys.argv[2:4]))
    else:
        leer(*map(Path, sys.argv[2:4]), *sys.argv[4:])
