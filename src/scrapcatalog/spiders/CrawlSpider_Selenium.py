import time
from scrapcatalog.items import ProductItem
from scrapy_selenium import SeleniumRequest
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class CRWSSpider(CrawlSpider):
    name = "crawl-spider-selenium"
    allowed_domains = ["conrad.com"]
    start_urls = ['https://www.conrad.com/o/embedded-microcontrollers-0214046']
    custom_settings = {'CLOSESPIDER_PAGECOUNT': 1000, 'CLOSESPIDER_ITEMCOUNT': 100,
                       'DOWNLOADER_MIDDLEWARES': {'scrapcatalog.middlewares.DownloadTimer': 0,
                                                  'scrapy_selenium.SeleniumMiddleware': 200,
                                                  'scrapcatalog.middlewares.SeleniumWaitingMiddleware': 201}}
    rules = (Rule(LinkExtractor(allow=start_urls[0])), Rule(LinkExtractor(allow='/p/'), callback='parse'))
    properties_locator = "//table[@class='table table-striped table-striped--dark technical-data__table']/tbody/tr"
    category_locator = None
    positions = 2
    wait_time = 5
    max_wait_time = 20
    wait_sintaxes = ['microdata', 'opengraph', 'microformat', 'json-ld', 'dublincore']
    output_file = 'items.jl'

    def _build_request(self, rule_index, link):
        return SeleniumRequest(
            url=link.url,
            callback=self._callback,
            errback=self._errback,
            meta=dict(rule=rule_index, link_text=link.text),
            wait_time=5,
        )

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
        item['Name'] = response.meta['Name']
        item['Category'] = response.meta['Category']

        # general properties
        item['StructuredData'] = response.meta['StructuredData']
        item['Properties'] = response.meta['Properties']

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
