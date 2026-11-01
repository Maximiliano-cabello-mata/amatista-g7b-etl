import os
import pymongo
from dotenv import load_dotenv

load_dotenv()

class MongoPipeline:
    def __init__(self, mongo_uri):
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client['conocimiento_3d']

    @classmethod
    def from_crawler(cls, crawler):
        # 1. Busca en los Raw Settings de Zyte. 2. Si no lo encuentra, usa tu .env local
        mongo_uri = crawler.settings.get('MONGO_URI') or os.getenv('MONGO_URI')
        
        if not mongo_uri:
            raise ValueError("Falta MONGO_URI en Zyte o en tu archivo .env")
            
        return cls(mongo_uri=mongo_uri)

    def process_item(self, item, spider):
        # Las arañas que guardan crudo para el lago (como "paginas") no escriben en MongoDB.
        if not getattr(spider, "guardar_en_mongo", True):
            return item
        self.db['foros_crudos'].insert_one(dict(item))
        return item

    def close_spider(self, spider):
        self.client.close()
