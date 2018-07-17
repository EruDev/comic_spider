# -*- coding: utf-8 -*-
import re
import random
import scrapy
from faker import Faker
from scrapy.http import Request
from ..items import ComicSpiderItem


class ComicSpider(scrapy.Spider):
    name = 'comic'
    allowed_domains = ['comic.kukudm.com']
    faker = Faker()
    server_img = 'http://n5.1whour.com/'
    server_link = 'http://comic.kukudm.com'
    start_urls = ['http://comic.kukudm.com/index.htm']

    custom_settings = {
        'CONCURRENT_REQUESTS': 64,
        'DOWNLOAD_DELAY': 0,
        'COOKIES_ENABLED': False,
        # 'LOG_LEVEL': 'INFO',
        # 'RETRY_ENABLED': False,
        'RETRY_TIMES': 15,
        'DEFAULT_REQUEST_HEADERS': {
            'user-agent': faker.user_agent(),
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'max-age=0',
            'Host': 'comic.kukudm.com',
            'Proxy-Connection': 'keep-alive'
        },
        'MONGO_URI': 'localhost:27017',
        'MONGO_DATABASE': 'comic',
        'PROXY_URL': 'http://localhost:5555/random',
        'ITEM_PIPELINES': {
            'comic_spider.pipelines.MongoPipeline': 301,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'comic_spider.middlewares.ProxyMiddleware': 543,
        },
    }

    def parse(self, response):
        """爬取漫画分类索引[A-Z]"""
        urls = response.xpath('//table[4]//a/@href').extract()
        for url in urls:

            yield Request(url=response.urljoin(url), callback=self.parse_category,
                          headers={'Referer': response.url})

    def parse_category(self, response):
        urls = response.xpath('//dd/a/@href').extract()
        for url in urls:

            yield Request(url=self.server_link + url, callback=self.parse_comic)

        nexts = response.xpath('//table[5]//tr//td[2]//table[1]//a[text()="下一页"]/@href').extract_first()
        if nexts:

            yield Request(url=self.server_link + nexts, callback=self.parse_category)

    def parse_comic(self, response):
        items = list()
        urls = response.xpath('//dd/a/@href').extract() # 这里拿到的url跟网站是有出入的, 网站上的url是错误的, 可能是个反爬策略
        dir_names = response.xpath('//dd/a/text()').extract()

        for idx in range(len(urls)):
            item = ComicSpiderItem()
            item['link_url'] = self.server_link + urls[idx]
            item['dir_name'] = dir_names[idx]
            items.append(item)

        for item in items:

            yield Request(url=item['link_url'], callback=self.parse_detail, meta={'item': item})

    def parse_detail(self, response):
        item = response.meta.get('item')
        item['link_url'] = response.url

        page_nums = response.xpath('//table[2]//td/text()').re(r'共(\d+)页')[0]
        prev_link = item['link_url'][:-5]

        for i in range(int(page_nums)):
            new_link = prev_link + str(i+1) + '.htm'

            yield Request(url=new_link, callback=self.parse_image, meta={'item': item})

    def parse_image(self, response):
        item = response.meta['item']
        item['link_url'] = response.url

        pattern_img1 = re.compile('src=\\\'"\+.*?\+"(.*?)\\\'>')
        pattern_img2 = re.compile('src="\+server\+"(.*?)>')
        url = re.findall(pattern_img1, response.text)

        if not url:
            url = re.findall(pattern_img2, response.text)

        item['img_url'] = self.server_img + url[0]
        # print("===============")
        # print(item['img_url'])

        yield item

