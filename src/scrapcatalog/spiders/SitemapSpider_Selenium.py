import time
from scrapcatalog.items import ProductItem
from scrapy.spiders.sitemap import *
from scrapy_selenium import SeleniumRequest


class SMSSpider(SitemapSpider):
    name = "sitemap-spider-selenium"
    allowed_domains = ["conrad.com"]
    sitemap_urls = ['https://www.conrad.com/sitemap.xml']
    sitemap_rules = [('/p/', 'parse')]
    custom_settings = {'CLOSESPIDER_PAGECOUNT': 1000, 'CLOSESPIDER_ITEMCOUNT': 100, 'DOWNLOADER_MIDDLEWARES':
        {'scrapcatalog.middlewares.DownloadTimer': 0, 'scrapy_selenium.SeleniumMiddleware': 200,
         'scrapcatalog.middlewares.SeleniumWaitingMiddleware': 201}}
    properties_locator = "//table[@class='table table-striped table-striped--dark technical-data__table']/tbody/tr"
    category_locator = None
    positions = 2
    wait_time = 5
    max_wait_time = 20
    wait_sintaxes = ['microdata', 'opengraph', 'microformat', 'json-ld', 'dublincore']
    output_file = 'items.jl'

    def _parse_sitemap(self, response):
        if response.url.endswith('/robots.txt'):
            for url in sitemap_urls_from_robots(response.text, base_url=response.url):
                yield Request(url, callback=self._parse_sitemap)
        else:
            body = self._get_sitemap_body(response)
            if body is None:
                logger.warning("Ignoring invalid sitemap: %(response)s",
                               {'response': response}, extra={'spider': self})
                return

            s = Sitemap(body)
            it = self.sitemap_filter(s)

            if s.type == 'sitemapindex':
                for loc in iterloc(it, self.sitemap_alternate_links):
                    if any(x.search(loc) for x in self._follow):
                        yield Request(loc, callback=self._parse_sitemap)
            elif s.type == 'urlset':
                for loc in iterloc(it, self.sitemap_alternate_links):
                    for r, c in self._cbs:
                        if r.search(loc):
                            # open('url_log.csv', 'a').write(loc + '\n')
                            yield SeleniumRequest(
                                url=loc,
                                callback=c,
                                wait_time=5
                            )
                            break

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