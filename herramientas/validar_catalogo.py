"""Validación sin dependencias externas del inventario de ofertas G7B."""
import json
from pathlib import Path

RUTA = Path(__file__).resolve().parents[1] / "infra" / "ofertas" / "catalogo.json"
GRUPOS = {"nucleo", "capacidad_opcional", "formacion_personal", "productividad_individual"}
ESTADOS = {"infraestructura_existente_por_verificar", "evaluar", "piloto_pendiente"}


def validar(datos):
    errores = []
    if datos.get("schema") != "g7b.ofertas/1":
        errores.append("Contrato del catálogo incorrecto")
    nombres = set()
    for i, item in enumerate(datos.get("ofertas", [])):
        nombre = item.get("servicio", "")
        if not nombre or nombre in nombres:
            errores.append(f"Oferta duplicada o sin nombre: {i} {nombre}")
        nombres.add(nombre)
        if item.get("grupo") not in GRUPOS or item.get("estado") not in ESTADOS:
            errores.append(f"Clasificación incorrecta de {nombre}")
        if item.get("conectado") is not False:
            errores.append(f"Conexión no comprobada marcada como verdadera: {nombre}")
        if not item.get("funcion") or not item.get("responsable"):
            errores.append(f"Faltan descripción o responsable: {nombre}")
        # Prohibir nombres de llaves y URL de firma SAS dentro del inventario.
        if any(c in json.dumps(item).lower() for c in ("sig=", "accountkey=", "mongodb+srv://")):
            errores.append(f"Posible secreto en la oferta {nombre}")
    if len(nombres) < 60:
        errores.append("Inventario insuficiente para el pack suministrado")
    if not {"Microsoft Azure", "GitHub", "Zyte", "MongoDB", "Deepnote", "Camber"} <= nombres:
        errores.append("Falta uno de los servicios esenciales")
    return errores


def main():
    datos = json.loads(RUTA.read_text(encoding="utf-8"))
    errores = validar(datos)
    print(f"Ofertas registradas: {len(datos['ofertas'])}")
    if errores:
        raise SystemExit("\\n".join(errores))
    print("G7B_OFERTAS_VALIDADO")


if __name__ == "__main__":
    main()
