# CEFAT4CITIES Scraper

## Usage

After installing the requirements.txt with:

```
pip install -r requirements.txt
```

The scrapers can be run with:

```
python start-spider.py --seedlist /location/of/seedlist --save_dir /location/of/save_dir > logfile.txt 2>&1
```
Using this command will start the scrapers and keep the logs in a file 'logfile.txt'

The seedlist is a plaintext file with on each new line a url.

The save_dir is used to create files tracking when the scraping has started for each website. This means that when the command is started again, it will skip the sites it has already started scraping for.

Alternatively the scraper can be run for a single website with:

```
python scrapy startspider FullSite -a url=www.example.com -a save_dir=/location/of/save_dir
```
