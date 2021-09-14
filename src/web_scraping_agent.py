from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.utils.project import get_project_settings
from src.scrapcatalog.spiders import SitemapSpider
from src.scrapcatalog.spiders import SitemapSpider_Selenium
from src.scrapcatalog.spiders import CrawlSpider
from src.scrapcatalog.spiders import CrawlSpider_Selenium
from scrapy.crawler import CrawlerRunner
from twisted.internet import reactor, defer
from scrapy.utils.log import configure_logging

@defer.inlineCallbacks
def crawl(runner):
    print('running rs-components')
    yield runner.crawl(SitemapSpider.SMSpider,
                       allowed_domains=["uk.rs-online.com"],
                       sitemap_urls=['https://uk.rs-online.com/sitemap.xml'],
                       sitemap_rules=[('/p/microcontrollers/', 'parse')],
                       properties_locator="//table[@data-testid='specification-attributes']/tbody/tr",
                       category_locator=None,
                       positions=2,
                       output_file='items_2.jl')
    print('running infinity-electron')
    yield runner.crawl(CrawlSpider.CRWSpider,
                       allowed_domains=["infinity-electron.com"],
                       start_urls=[
                           'https://www.infinity-electron.com/Integrated-Circuits(ICs)/Embedded-Microcontrollers.aspx'],
                       rules=(
                           Rule(LinkExtractor(allow='_page')),
                           Rule(LinkExtractor(allow='/product/'), callback='parse')),
                       properties_locator="//div[@class='specifications']/table/tr",
                       category_locator="//div[@class='navigation']/a[last()]",
                       positions=4,
                       output_file='items_2.jl')
    print('running conrad-electronics')
    yield runner.crawl(CrawlSpider_Selenium.CRWSSpider,
                       allowed_domains=["conrad.com"],
                       start_urls=['https://www.conrad.com/o/embedded-microcontrollers-0214046'],
                       rules=(Rule(LinkExtractor(allow='https://www.conrad.com/o/embedded-microcontrollers-0214046')),
                              Rule(LinkExtractor(allow='/p/'), callback='parse')),
                       properties_locator="//table[@class='table table-striped table-striped--dark technical-data__table']/tbody/tr",
                       category_locator=None,
                       positions=2,
                       output_file='items_2.jl')
    reactor.stop()

    """# sitemap spider for infinity electron
    # it doesn't work because in the sitemap links have infinity-element instead of infinity-electron!
    yield runner.crawl(SitemapSpider.SMSpider,
                       allowed_domains=["infinity-electron.com"],
                       sitemap_urls=['https://www.infinity-electron.com/sitemap.xml'],
                       sitemap_rules=[('/p', 'parse')],
                       properties_locator="//div[@class='specifications']/table/tr",
                       category_locator="//div[@class='navigation']/a[last()]",
                       positions=4)
    # sitemap spider SELENIUM for Conrad Electronics
    yield runner.crawl(SitemapSpider_Selenium.SMSSpider,
                       allowed_domains=["conrad.com"],
                       sitemap_urls=['https://www.conrad.com/sitemap.xml'],
                       sitemap_rules=[('/p/', 'parse')],
                       properties_locator="//table[@class='table table-striped table-striped--dark technical-data__table']/tbody/tr",
                       category_locator=None,
                       positions=2,
                       wait_time=5,
                       max_wait_time=20,
                       wait_sintaxes=['microdata', 'opengraph', 'microformat', 'json-ld', 'dublincore'],
                       output_file='sitemap_conrad_items.jl')
    # crawl spider SELENIUM for rs-components
    # In this website, category pages do not have embedded the links for the next pages, rather they are generated
    # with a script once the user clicks the navigation button.
    yield runner.crawl(CrawlSpider_Selenium.CRWSSpider,
                       allowed_domains=["uk.rs-online.com"],
                       start_urls=[
                           'https://uk.rs-online.com/web/c/semiconductors/processors-microcontrollers/microcontrollers/'],
                       rules=(Rule(LinkExtractor(allow='/p/'), callback='parse'),),
                       properties_locator="//table[@data-testid='specification-attributes']/tbody/tr",
                       category_locator=None,
                       positions=2)"""


def main():
    configure_logging()
    runner = CrawlerRunner(settings=get_project_settings())
    crawl(runner)
    reactor.run()


if __name__ == '__main__':
    main()
