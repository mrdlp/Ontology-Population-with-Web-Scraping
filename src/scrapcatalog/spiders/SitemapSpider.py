import time
import scrapy
import extruct
from scrapcatalog.items import ProductItem


class SMSpider(scrapy.spiders.SitemapSpider):
    name = "sitemap-spider"
    allowed_domains = ["uk.rs-online.com"]
    sitemap_urls = ['https://uk.rs-online.com/sitemap.xml']
    sitemap_rules = [('/p/microcontrollers/', 'parse')]
    custom_settings = {'CLOSESPIDER_PAGECOUNT': 1000, 'CLOSESPIDER_ITEMCOUNT': 100,
                       'DOWNLOADER_MIDDLEWARES': {'scrapcatalog.middlewares.DownloadTimer': 0,
                                                  'scrapcatalog.middlewares.RequestEditorIE': 1}}
    properties_locator = "//table[@data-testid='specification-attributes']/tbody/tr"
    category_locator = None
    positions = 2
    output_file = 'items.jl'

    def parse(self, response):
        item = ProductItem()

        # basic information
        item['ProductLink'] = response.url
        item['Source'] = self.allowed_domains[0]
        item['StartTime'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(response.meta['__start_time']))
        item['EndTime'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(response.meta['__end_time']))
        item['DownloadTime'] = response.meta['__end_time'] - response.meta['__start_time']
        item['Organization'] = self.allowed_domains[0].split(".")[-2]

        # mandatory fields
        item['Name'] = self.get_name(response)
        item['Category'] = self.get_category(response, self.category_locator)

        # general properties
        item['StructuredData'] = extruct.extract(response.text, uniform=True)
        item['Properties'] = self.get_specifications(response, self.properties_locator, self.positions)

        yield item

    @staticmethod
    def get_name(response):
        name = response.xpath("head/title/text()").get()
        return name

    @staticmethod
    def get_category(response, locator=None):
        if locator:
            category = response.xpath(locator + "/text()").get()
            return category
        return None

    @staticmethod
    def get_specifications(response, locator=None, positions=2):
        keys = []
        values = []
        if locator:
            for items in response.xpath(locator):
                for p in range(1, positions + 1, 2):
                    k = items.xpath("./*[position()=" + str(p) + "]/text()").get()
                    v = items.xpath("./*[position()=" + str(p + 1) + "]/text()").get()
                    if k:
                        keys.append(k)
                        if v:
                            values.append(v)
                        else:
                            values.append(None)
            properties = dict(zip(keys, values))
            return properties
        return None
