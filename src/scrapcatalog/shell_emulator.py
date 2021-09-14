from scrapy.cmdline import execute
import sys
sys.argv = ['scrapy', 'shell', 'http://scrapy.org']
execute()