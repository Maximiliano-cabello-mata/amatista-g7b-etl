"""Peticiones HTTP educadas: identificación, tiempo límite, robots.txt y peticiones condicionales."""
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urlparse

AGENTE = "G7B-bot/0.1 (Geodar Radar; +https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl)"
_ROBOTS = {}

# APIs públicas y documentadas: se rigen por sus propias condiciones (límites, llave, identificación),
# no por el robots.txt del sitio, que es para rastreadores de páginas. Solo se agregan aquí APIs cuyo
# uso automatizado está documentado por su dueño.
APIS_OFICIALES = {"api.github.com", "api.stackexchange.com", "api.polyhaven.com"}


@dataclass
class Respuesta:
    estado: int
    cabeceras: dict = field(default_factory=dict)
    contenido: bytes = b""

    @property
    def texto(self):
        return self.contenido.decode("utf-8", errors="replace")


def permitido(url, obtener_robots=None):
    """Respeta robots.txt; si no se puede leer, se permite (como hacen los buscadores)."""
    partes = urlparse(url)
    if partes.hostname in APIS_OFICIALES:
        return True
    base = f"{partes.scheme}://{partes.netloc}"
    if base not in _ROBOTS:
        lector = urllib.robotparser.RobotFileParser()
        try:
            if obtener_robots:
                lector.parse(obtener_robots(base + "/robots.txt").splitlines())
            else:
                lector.set_url(base + "/robots.txt")
                lector.read()
        except Exception:
            lector = None
        _ROBOTS[base] = lector
    lector = _ROBOTS[base]
    return True if lector is None else lector.can_fetch(AGENTE, url)


def obtener(url, cabeceras=None, tiempo=30):
    import requests

    if not permitido(url):
        return Respuesta(999, {"motivo": "robots.txt no lo permite"})
    r = requests.get(url, headers={"User-Agent": AGENTE, **(cabeceras or {})}, timeout=tiempo)
    return Respuesta(r.status_code, {k.lower(): v for k, v in r.headers.items()}, r.content)
