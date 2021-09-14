# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ProductItem(scrapy.Item):
    # basic information
    ProductLink = scrapy.Field()
    StartTime = scrapy.Field()
    EndTime = scrapy.Field()
    DownloadTime = scrapy.Field()
    Source = scrapy.Field()

    # general properties
    StructuredData = scrapy.Field()
    Properties = scrapy.Field()

    # mandatory fields
    Category = scrapy.Field()
    Organization = scrapy.Field()
    Name = scrapy.Field()

    # Extra
    # CategoryPath = scrapy.Field()


    # specifications, this field is populated as a dictionary following the pattern
    # {property1: value1, property2: value2,...}

