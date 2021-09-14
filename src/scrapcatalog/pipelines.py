# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import json
from pathlib import Path
from src.utils import get_project_root
# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class StructuredDataPipeline:
    def process_item(self, item, spider):
        organization = ''
        product_name = ''
        category = ''
        structured_data = {}
        category_path = ''
        for iformat in item['StructuredData'].items():
            for element in iformat[1]:

                # process Schema.org annotations
                if element.get('@context') == 'http://schema.org/':

                    # get category and category path
                    if element.get('@type') == 'BreadcrumbList' and element.get('itemListElement'):
                        ordered_category_path = [None] * len(element.get('itemListElement'))
                        for path_element in element.get('itemListElement'):
                            ordered_category_path[path_element['position'] - 1] = path_element['item']['name']
                        category = ordered_category_path[-1]
                        category_path = '_'.join(ordered_category_path)

                    # get Organization information
                    elif element.get('@type') == 'Organization':
                        organization = element.get('name')

                    # get product information
                    elif element.get('@type') == 'Product':
                        for spec in element.items():
                            # extract offer info
                            if spec[0] == 'offers':
                                structured_data['priceCurrency'] = spec[1].get('priceCurrency')
                                structured_data['price'] = spec[1].get('price')
                                structured_data['priceCurrency'] = spec[1].get('priceCurrency')
                                structured_data['availability'] = spec[1].get('availability')
                            # extract other product info
                            else:
                                name = spec[0]
                                value = spec[1]
                                if name in ['@context', '@type', 'image']:
                                    pass
                                elif name == 'name':
                                    product_name = value
                                elif isinstance(value, str):
                                    structured_data[name] = value
                                else:
                                    try:
                                        structured_data[name] = value.get('name')
                                    except:
                                        pass
        # update item
        item['StructuredData'] = structured_data
        if category:
            item['Category'] = category
        if organization:
            item['Organization'] = organization
        if product_name:
            item['Name'] = product_name

        return item


class JsonWriterPipeline:
    file = None

    def open_spider(self, spider):
        root = get_project_root()
        myfile = 'src/Data/%s' %spider.output_file
        self.file = open(Path(root, myfile).resolve(), 'a')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(ItemAdapter(item).asdict()) + "\n"
        self.file.write(line)
        return item
