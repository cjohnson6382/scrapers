# Scrapy settings for gscholar project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

BOT_NAME = 'gscholar'
BOT_VERSION = '1.0'

SPIDER_MODULES = ['gscholar.spiders']
NEWSPIDER_MODULE = 'gscholar.spiders'
DEFAULT_ITEM_CLASS = 'gscholar.items.GscholarItem'
USER_AGENT = '%s/%s' % (BOT_NAME, BOT_VERSION)
#DOWNLOAD_DELAY = 45.0
