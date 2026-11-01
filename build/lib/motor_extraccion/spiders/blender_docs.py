import scrapy
from datetime import datetime

class BlenderDocsSpider(scrapy.Spider):
    name = 'blender_docs'
    allowed_domains = ['docs.blender.org']
    start_urls = ['https://docs.blender.org/manual/en/latest/advanced/scripting/index.html']

    def parse(self, response):
        # Extraemos los elementos de la tabla de contenido
        for section in response.css('li.toctree-l1'):
            yield {
                'titulo': section.css('a::text').get(),
                'enlace': response.urljoin(section.css('a::attr(href)').get()),
                'fuente': 'Blender Docs',
                'fecha_extraccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
