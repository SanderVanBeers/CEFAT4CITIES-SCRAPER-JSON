from multiprocessing import Pool
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import fullsite.spiders.fullsite
from fullsite.spiders.fullsite import FullSiteSpider
import argparse
import os
 
def start_scraper(url):
    process = CrawlerProcess(get_project_settings())
    process.crawl(FullSiteSpider, url=url, save_dir = SAVE_DIR)
    process.start()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--seedlist", dest="seedlist", help="List of websites to be scraped.", required=True)
    parser.add_argument("--save_dir", dest="save_dir", help="output directory", required=True)
    args = parser.parse_args()

    SEEDLIST = args.seedlist
    SAVE_DIR = args.save_dir
    with open(SEEDLIST, 'r') as seedlist:
        urls = seedlist.read().splitlines()
        pool = Pool()
        pool.map(start_scraper, urls)
        pool.close()
        pool.join()
