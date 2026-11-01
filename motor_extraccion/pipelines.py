"""Pipeline de MongoDB: idempotente y solo para las arañas que lo piden (guardar_en_mongo = True).

Lo normal en G7B es que lo crudo vaya al lago y que a MongoDB llegue solo lo aceptado por el embudo
(g7b_ingesta/publicar.py). Este pipeline queda para arañas que escriban directo, con estas reglas:
- un documento por doc_id (índice único);
- solo se escribe si hash_contenido cambió; si no, no se toca;
- la fecha de la primera vez se conserva.
"""
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def guardar(coleccion, datos):
    """Inserta o actualiza por doc_id. Devuelve "nuevo", "actualizado" o "sin_cambios"."""
    previo = coleccion.find_one({"doc_id": datos["doc_id"]}, {"hash_contenido": 1})
    if previo and previo.get("hash_contenido") == datos.get("hash_contenido"):
        return "sin_cambios"
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    coleccion.update_one({"doc_id": datos["doc_id"]},
                         {"$set": {**datos, "actualizado_en": ahora}, "$setOnInsert": {"creado_en": ahora}},
                         upsert=True)
    return "actualizado" if previo else "nuevo"


class MongoPipeline:
    def __init__(self, mongo_uri, base, coleccion):
        self.mongo_uri, self.base, self.nombre_coleccion = mongo_uri, base, coleccion
        self.cliente = None
        self.coleccion = None

    @classmethod
    def from_crawler(cls, crawler):
        s = crawler.settings
        pipeline = cls(s.get("MONGO_URI") or os.getenv("MONGO_URI"), s.get("MONGO_DATABASE", "conocimiento_3d"),
                       s.get("MONGO_COLLECTION", "documentos"))
        pipeline.crawler = crawler
        return pipeline

    # spider=None: Scrapy 2.11 pasa la araña; las versiones nuevas ya no (se toma de crawler).
    def _arana(self, spider):
        return spider or getattr(getattr(self, "crawler", None), "spider", None)

    def open_spider(self, spider=None):
        spider = self._arana(spider)
        if not getattr(spider, "guardar_en_mongo", False):
            return  # el crudo va al lago: no hace falta ni conectarse
        if not self.mongo_uri:
            raise ValueError("Falta MONGO_URI (Doppler, Raw Settings de Zyte o .env local)")
        import pymongo

        self.cliente = pymongo.MongoClient(self.mongo_uri)
        self.coleccion = self.cliente[self.base][self.nombre_coleccion]
        self.coleccion.create_index("doc_id", unique=True)

    def process_item(self, item, spider=None):
        spider = self._arana(spider)
        if self.coleccion is None:
            return item
        datos = dict(item)
        if "doc_id" not in datos:
            logger.warning("Item sin doc_id: no se guarda en MongoDB (%s)", datos.get("url"))
            return item
        resultado = guardar(self.coleccion, datos)
        if getattr(spider, "crawler", None):
            spider.crawler.stats.inc_value(f"g7b/mongo/{resultado}")
        return item

    def close_spider(self, spider=None):
        if self.cliente:
            self.cliente.close()
