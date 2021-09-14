# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

# useful for handling different item types with a single interface
import time
import extruct
from scrapy.http import Response, Request
from scrapy.http import HtmlResponse
from scrapy import signals
from scrapy_selenium import SeleniumRequest


class ScrapcatalogSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class SeleniumWaitingMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        """
        When crawling, start urls are not called using selenium, here we generate a selenium request for those urls
        that are included in the list of start urls and don't have a selenium request
        """
        if not isinstance(request, SeleniumRequest) and request.url in spider.start_urls:
            return SeleniumRequest(url=request.url, callback=request.callback)
        return None

    def process_response(self, request, response, spider):
        """
        1 - imports spider's parse functions and parameters
        2 - in a loop, parses new response from driver and checks against old response values
        3 - if parsed values don't change during x consecutive seconds, return response
        4 - save parsed valued in meta dicctionary to avoid double efforts in parse module inside spider
        """

        if not isinstance(request, SeleniumRequest):
            return response

        timeout = time.time() + spider.wait_time
        max_timeout = time.time() + spider.max_wait_time
        structured_data = extruct.extract(response.text, uniform=True, syntaxes=spider.wait_sintaxes)
        name = spider.get_name(response)
        category = spider.get_category(response, spider.category_locator)
        properties = spider.get_specifications(response, spider.properties_locator, spider.positions)

        while True:
            body = str.encode(response.request.meta['driver'].page_source)
            new_response = HtmlResponse(response.url, body=body, encoding='utf-8', request=request)
            structured_data2 = extruct.extract(body, uniform=True, syntaxes=spider.wait_sintaxes)
            name2 = spider.get_name(new_response)
            category2 = spider.get_category(new_response, spider.category_locator)
            properties2 = spider.get_specifications(new_response, spider.properties_locator, spider.positions)

            if (structured_data != structured_data2) or (name != name2) or (category != category2) or \
                    properties != properties2:
                timeout = time.time() + spider.wait_time
                structured_data = structured_data2
                name = name2
                category = category2
                properties = properties2

            elif time.time() > timeout:
                break

            if time.time() > max_timeout:
                print('max timeout reached!')
                break

            time.sleep(1)

        request.meta['Name'] = name
        request.meta['Category'] = category
        request.meta['Properties'] = properties
        request.meta['StructuredData'] = extruct.extract(body, uniform=True)

        return new_response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class DownloadTimer:

    def process_request(self, request, spider):
        request.meta['__start_time'] = time.time()
        # this not block middlewares which are has greater number then this
        return None

    def process_response(self, request, response, spider):
        request.meta['__end_time'] = time.time()
        return response  # return response coz we should

    def process_exception(self, request, exception, spider):
        request.meta['__end_time'] = time.time()
        return Response(
            url=request.url,
            status=110,
            request=request)


class RequestEditorIE:

    def process_request(self, request, spider):
        if 'infinity-element' in str(request.url):
            url = request.url.replace("infinity-element", "infinity-electron")
            return Request(url, callback=request.callback)
        return None