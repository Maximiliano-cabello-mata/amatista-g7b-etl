import pytest

from g7b_almacen.esquema_cubo import hechos_separados

CANONICOS = ["plata/mediciones.parquet", "oro/parquet/repeticiones.parquet", "oro/parquet/linaje.parquet"]
CLASES = ["plata/hechos_directos.parquet", "plata/hechos_relativos.parquet"]


def v2(archivos, **campos):
    return {"contrato": "g7b.cubo/2", "archivos": dict.fromkeys(archivos), **campos}


def test_distingue_las_dos_variantes_sin_reinterpretar_mediciones():
    assert not hechos_separados(v2(CANONICOS))
    assert hechos_separados(v2(CLASES, directas={}, relativas={}))


@pytest.mark.parametrize("manifiesto", [
    v2(CANONICOS + CLASES, directas={}, relativas={}), v2(CANONICOS[:1]), v2(CLASES, directas={}),
    v2(CANONICOS, relativas={}), v2(CLASES + CANONICOS[:1], directas={}, relativas={}),
])
def test_rechaza_inventarios_ambiguos(manifiesto):
    with pytest.raises(ValueError, match="ambigua"):
        hechos_separados(manifiesto)
