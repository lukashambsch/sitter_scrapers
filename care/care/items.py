# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class Job(scrapy.Item):
    name = scrapy.Field()
    url = scrapy.Field()


class Sitter(scrapy.Item):
    name = scrapy.Field()
    url = scrapy.Field()
