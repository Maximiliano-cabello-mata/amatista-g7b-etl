# Configuración de Scrapy para G7B (local y en Zyte Scrapy Cloud).
# Los pipelines se declaran aquí: ya no hace falta pegarlos en los Raw Settings de Zyte.
import os

try:  # .env local, para correr en tu PC; en Zyte las variables vienen de sus ajustes
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BOT_NAME = "motor_extraccion"
SPIDER_MODULES = ["motor_extraccion.spiders"]
NEWSPIDER_MODULE = "motor_extraccion.spiders"

USER_AGENT = "G7B-bot/0.1 (+https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl)"

# Respeto a los servidores: robots.txt, una petición a la vez por dominio y velocidad adaptable.
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1.0
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
HTTPCACHE_ENABLED = False

# Las arañas guardan lo crudo en Zyte y de ahí pasa al lago (zyte_a_lago); el embudo filtra después.
# MongoPipeline solo escribe para arañas con guardar_en_mongo = True (ninguna de las actuales).
ITEM_PIPELINES = {
    "motor_extraccion.pipelines.MongoPipeline": 300,
}

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "conocimiento_3d")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "documentos")

FEED_EXPORT_ENCODING = "utf-8"
