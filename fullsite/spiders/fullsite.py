# -*- coding: UTF-8 -*-

import os
import re
import scrapy
import uuid
import datetime
import time
import logging
from datetime import date
import langdetect
from datetime import date
from langdetect import detect
from urllib.parse import urlparse
from urllib.parse import parse_qs
from lxml.html.clean import Cleaner
from lxml import html
from scrapy.http import HtmlResponse
from scrapy.exceptions import NotConfigured
from base64 import b64encode
import html2text
from bs4 import BeautifulSoup
import pickle

class FullSiteSpider(scrapy.Spider):
    
    pwd = os.getcwd()
    name = "FullSite"

    MAX_PATH_DEPTH = 15
    logger = logging.getLogger('FullSiteSpider')

    ignored_extensions = [".jpg", ".mp3", ".mp4", ".wmv", ".avi",
                          ".png", ".gif", ".zip", ".iso", ".exe", ".tif", ".mov"]

    FT_REGEX= r"pdf|doc|docx"
    FILES_EXTENSION= r"\.(" + FT_REGEX + r")(\/[a-zA-Z0-9-]*)?"
    ONLY_DOCS=False

    def __init__(self, *args, **kwargs):

        super(FullSiteSpider, self).__init__(*args, **kwargs)

        self.url = kwargs.get('url')
        if (not self.url):
            raise NotConfigured(
                "Expecting a 'url' property to be configured, pointing to the first page on the site")

        save_dir_root = kwargs.get('save_dir')
        if (not save_dir_root):
            raise NotConfigured(
                "Expecting a save_dir property to be configured where the data must be stored")
        self.ONLY_DOCS = kwargs.get('only_docs')

        self.langs = kwargs.get('langs')
        if not self.langs:
            self.langs = []
        else:
            self.langs = self.langs.split(',')

        self.save_dir = save_dir_root + "/" + \
            self.url.replace('/', '').replace(':', '.')

        self.docs_dir = self.save_dir + "/docs"

        if not os.path.exists(self.save_dir):
            os.makedirs(self.docs_dir)
        else:
            if not os.path.exists(self.docs_dir):
                os.makedirs(self.docs_dir)
                # html was already scraped for this site, only scrape docs
                self.ONLY_DOCS = True
            else:
                raise NotConfigured(
                    "Output directory '%s' already exists! Skipping this site!" % self.docs_dir)

        self.inprogress_file = self.save_dir + "/inprogress"
        if os.path.isfile(self.inprogress_file):
            raise NotConfigured(
                "File '%s' already exists! Make sure no scrapy is currently running on this site!" % self.inprogress_file)
        else:
            with open(self.inprogress_file, "w") as in_progress_file:
                in_progress_file.write("Started on %s" % time.strftime("%c"))

        self.logger.debug("Saving site in %s", self.save_dir)

        self.url_forbidden_prefixes = ["#", "javascript"]

        self.search_domains = set()
        parsed_uri = urlparse(self.url)
        self.search_domains.add(
            'http://{uri.netloc}/'.format(uri=parsed_uri))
        self.search_domains.add(
            'https://{uri.netloc}/'.format(uri=parsed_uri))

        self.cleaner = Cleaner(style=True, links=True, add_nofollow=True,
                               page_structure=False, safe_attrs_only=False)

    def start_requests(self):

        headers = {}
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 6.2; WOW64; rv:22.0) Gecko/20100101 Firefox/22.0"
        headers["DNT"] = "1"
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        headers["Accept-Encoding"] = "deflate"
        headers["Accept-Language"] = "en-US,en;q=0.5"

        request = scrapy.Request(url=self.url, headers={
                                 'Referer': self.url}, callback=self.parse)
        request.meta['origin'] = ""
        yield request

    def parse(self, response):
        parsed_uri = urlparse(response.url)
        self.search_domains.add(
            'http://{uri.netloc}/'.format(uri=parsed_uri))
        self.search_domains.add(
            'https://{uri.netloc}/'.format(uri=parsed_uri))

        detected_language = ""
        # indicates if it should be processed in items pipeline
        skip = False

        if isinstance(response, HtmlResponse) and not self.ONLY_DOCS:
            
            name = str(uuid.uuid4()) + ".html"
            filename = self.save_dir + "/" + name

            clean_body = self.cleaner.clean_html(response.body)
            
            content = self.htmlToText(clean_body)
            
            detected_language = detect(
                html.fromstring(clean_body).text_content())

            self.logger.debug("Detected language '%s' for: %s",
                              detected_language, response.url)
            html_content = b64encode(response.body).decode('UTF8')
            url = response.url

            pdf_urls = [url for url in response.css('a::attr(href)').extract() if '.pdf'.casefold() in url]
            pdf_docs = []
            for url in pdf_urls:
                if (url.startswith('http://') or url.startswith('https://')):
                    pdf_docs.append(url)
                else:
                    pdf_docs.append(response.urljoin(url))


            pdf_docs = [response.urljoin(url) for url in pdf_urls]
            yield {
                'url': response.url,
                'html_content': html_content,
                'date': datetime.datetime.now().isoformat(),
                'language': detected_language,
                'pdf_docs': pdf_docs
            }


        if isinstance(response, HtmlResponse):

            urls = response.css('a::attr(href)').extract()
            loophole = False
            for url in urls:
                
                today = date.today()
                keyword = re.search("agenda", url)
                match = re.search(r'\d{4}-\d{2}-\d{2}', url)
                if keyword:
                    try:
                        
                        date_time_str = match.group()
                        date_time_obj = datetime.datetime.strptime(date_time_str, '%Y-%m-%d').date()
                        if date_time_obj > today:
                            self.logger.warn(
                                "Date %s appears to be set in the future. Stopping here!", url)
                    except:
                        date_time_str = None

                if not (url.startswith('http://') or url.startswith('https://')):
                    url = response.urljoin(url)

                parsed_uri = urlparse(url)
                parsed_orig_uri = urlparse(response.url)

                domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)

                if all(not url.startswith(x) for x in self.url_forbidden_prefixes):
                    if domain in self.search_domains:
                            
                        if url.count('/') < self.MAX_PATH_DEPTH:
                           
                            if "search" in url.lower():
                                self.logger.warn(
                                    "Path %s appears to be a search field. Stopping here!", url)
                            else:
                                if parsed_uri.path and parsed_uri.path[-4:] in self.ignored_extensions:
                                    self.logger.warn(
                                        "Path %s contains ignored extension. Stopping here!", url)
                                else:
                                    loophole = self.detect_loop_hole(parsed_uri, parsed_orig_uri)
                                    if loophole:
                                        self.logger.warn(
                                            "Path %s looks like a loophole. Stopping here!", url)
                                    else:
                                        request = response.follow(
                                            url, headers={'Referer': response.url}, callback=self.parse)
                                        request.meta['origin'] = response.url
                                        yield request
                        else:
                            self.logger.warn(
                                "Reached maxs path depth for %s. Stopping here!", url)
                    else:
                        self.logger.debug("Not an allowed domain: %s", url)
                else:
                    self.logger.debug("In forbidden prefixes: %s", url)


    def detect_loop_hole(self, new_uri, previous_uri):
        # temporary solution to avoid treating pages on websites as loops, should be improved
        a_previous_uri = str(previous_uri)
        keyword = re.search("page", a_previous_uri)
        if keyword is None:
            if previous_uri.path == new_uri.path:
                if new_uri.query and previous_uri.query:
                    if not self.hasNewKeys(parse_qs(new_uri.query), parse_qs(previous_uri.query)):
                        return True
                    if self.query_parameter_occurences_exceeds(new_uri.query, 4):
                        return True
            else:  # if new url is not a page and not identical to the previous url still check for repeated params
                for param in re.findall('\W(.+?)&', str(previous_uri.query)):
                    if param in str(new_uri.query):
                        print("this " + param + " is being repeated")
                        return True

        else:  # if new url is a page still check for repeated params
             for param in re.findall('\W(.+?)&', str(previous_uri.query)):
                 if param in str(new_uri.query):
                     print("this " + param + " is being repeated")
                     return True
        return False
                                    
    def hasNewKeys(self, first, second):
        for key in second.keys():
            if not key in first.keys():
                return True
        return False

    def query_parameter_occurences_exceeds(self, uri_query, max_occurences):
        array = parse_qs(uri_query)
        for key in array:
            if len(array[key]) > max_occurences:
                return True
        return False
    
    def htmlToText(self, html):
        #Whitelist with all tags we want to keep
        whitelist = ['p','title','h1']
        soup = BeautifulSoup(html, features='lxml')
        text = []
        for tag in soup.find_all(True):
                try:
                    if tag.string and not tag.string.isspace():
                        if tag.name in whitelist:
                            text.append(tag.string.strip())
                except RecursionError:
                    print(f"Recursion error")
        text = ' '.join(text)
        return text

