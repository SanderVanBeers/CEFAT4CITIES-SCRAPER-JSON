# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import json
from itemadapter import ItemAdapter
class FullsitePipeline:
    def open_spider(self, spider):
        self.file = open('items.jl', 'a')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        if len(item['pdf_docs']) > 1:
            line = json.dumps(ItemAdapter(item).asdict()) + "\n"
            self.file.write(line)
            return item
        
