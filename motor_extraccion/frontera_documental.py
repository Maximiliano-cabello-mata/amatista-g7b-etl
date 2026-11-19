"""Selección experimental de la próxima página documental, sin red ni etiquetas de evaluación."""
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit


def palabras(texto):
    base = unicodedata.normalize("NFKD", texto.casefold())
    limpio = "".join(letra for letra in base if not unicodedata.combining(letra))
    return set(re.findall(r"[^\W_]+", limpio))


def jaccard(a, b):
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def calificar(url, ancla, encabezado, temas, profundidad):
    ruta = palabras(unquote(urlsplit(url).path))
    etiqueta = palabras(ancla)
    senal = (0.60 * jaccard(etiqueta, temas) + 0.25 * jaccard(ruta, temas)
             + 0.15 * jaccard(palabras(encabezado), temas))
    puente = bool((etiqueta | palabras(urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]))
                  & {"indice", "index", "catalogo", "catalog", "referencia", "reference"})
    return senal * 0.85 ** max(0, profundidad - 1), puente


@dataclass
class Candidato:
    url: str
    profundidad: int
    orden: int
    puntuacion: float
    puente: bool


class Frontera:
    estrategias = {"amplitud", "foco", "foco_puentes"}

    def __init__(self, estrategia, presupuesto):
        if estrategia not in self.estrategias or presupuesto < 1:
            raise ValueError("Estrategia desconocida o presupuesto inferior a uno")
        self.estrategia = estrategia
        self.presupuesto = presupuesto
        self.pendientes = {}
        self.visitadas = set()
        self.turnos = 0
        self.orden = 0

    def ofrecer(self, url, profundidad=0, puntuacion=0.0, puente=False):
        if url in self.visitadas:
            return
        anterior = self.pendientes.get(url)
        if anterior is None:
            self.pendientes[url] = Candidato(url, profundidad, self.orden, puntuacion, puente)
            self.orden += 1
        else:
            anterior.profundidad = min(anterior.profundidad, profundidad)
            anterior.puntuacion = max(anterior.puntuacion, puntuacion)
            anterior.puente |= puente

    def siguiente(self):
        if not self.pendientes or len(self.visitadas) >= self.presupuesto:
            return None
        candidatos = self.pendientes.values()
        semillas = [c for c in candidatos if c.profundidad == 0]
        por_amplitud = lambda c: (c.profundidad, c.orden)
        if semillas:
            elegido = min(semillas, key=por_amplitud)
        elif self.estrategia == "amplitud":
            elegido = min(candidatos, key=por_amplitud)
        else:
            self.turnos += 1
            puentes = []
            if self.estrategia == "foco_puentes" and self.turnos % 3 == 0:
                puentes = [c for c in candidatos if c.puente]
            if puentes:
                elegido = min(puentes, key=por_amplitud)
            else:
                elegido = min(candidatos, key=lambda c: (-c.puntuacion, c.profundidad, c.orden))
        del self.pendientes[elegido.url]
        self.visitadas.add(elegido.url)
        return elegido
