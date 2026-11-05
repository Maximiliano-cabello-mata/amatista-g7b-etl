"""El lago de datos de G7B en Azure Blob Storage (zonas bronce, plata y oro; ver docs/PLAN.md, sección 7)."""
from .lago import Lago, ruta_bronce
from .memoria import LagoMemoria

__all__ = ["Lago", "LagoMemoria", "ruta_bronce"]
