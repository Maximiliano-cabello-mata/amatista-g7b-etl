"""Distingue las dos variantes propuestas de g7b.cubo/2 por el inventario verificado con SHA-256."""


def hechos_separados(manifiesto):
    contrato = manifiesto["contrato"]
    if contrato == "g7b.cubo/1":
        return False
    if contrato == "g7b.cubo/3":
        return True
    if contrato != "g7b.cubo/2":
        raise ValueError("contrato de cubo desconocido")
    archivos = set(manifiesto["archivos"])
    canonicos = {"plata/mediciones.parquet", "oro/parquet/repeticiones.parquet", "oro/parquet/linaje.parquet"}
    por_clase = {"plata/hechos_directos.parquet", "plata/hechos_relativos.parquet"}
    if canonicos <= archivos and not por_clase & archivos and not {"directas", "relativas"} & manifiesto.keys():
        return False
    if por_clase <= archivos and not canonicos & archivos and {"directas", "relativas"} <= manifiesto.keys():
        return True
    raise ValueError("variante de g7b.cubo/2 incompleta o ambigua")
