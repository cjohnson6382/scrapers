import re
import MySQLdb
import json

from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.contrib.spiders import CrawlSpider, Rule
from gscholar.items import GscholarItem

from scrapy.http import Request
from scrapy.http import FormRequest

class CaseScraperSpider(CrawlSpider):
	name = 'case_scraper'
	allowed_domains = ['scholar.google.com']

	start_urls = ['http://scholar.google.com/']

	conn = MySQLdb.connect(host = "localhost", user = "SOMEUSER", passwd = "SOMEPASSWORD", db = "SOMEDB")
	cursor = conn.cursor()
	both_citations = {}

	def parse(self, response):
		# grab a bunch of citations from the database--only ones that don't use the special LEXIS citation notation--then put them into the citations variable
		self.cursor.execute("""select citation from cases where citation not like '%LEXIS%' and case_text is NULL limit 1000""")
		citations = self.cursor.fetchall()

		for citation in citations:
			# strip all the junk characters out of the citation and put it into the both_citations{} dict
			fixed_citation = re.sub(r'[\s|\.]', r'', citation[0])
			self.both_citations[fixed_citation] = citation[0]
			yield FormRequest.from_response(response, formdata={'as_sdt':'2,5', 'q':citation[0]}, callback=self.after_search)

	# this function gets the desired citation from the URL of the new page,
	#	then tries to find that citation among the search results on the current page
	def after_search(self, response):
	# get the desired citation from the URL
		# extract the citation from the previous page by re.search'ing the URL
		match = re.search(r'&q=(?P<volume>\d+)\+(?P<reporter>.*?)\+(?P<page>\d+)&hl=', str(response.request))

		citation_from_url = match.group('volume') + match.group('reporter') + match.group('page')
		citation_from_url = re.sub(r'[\s|\.|\+]', r'', citation_from_url)
		
	# extract the information from the current page
		# create a selector
		hxs = HtmlXPathSelector(response)
		# grab all the divs on the page that have citations in them
		divs = (hxs.select('/html/body/div[descendant::div[contains(@class, "gs_a")]]'))

	# for each div that the selector found, determine whether it matches with the citation from the URL
		for div in divs:
			# the div comes as a list, with a bunch of <b> tags mixed in,
			#	we first remove all the HTML, strip the spaces, and then join all of these into a single citation
			cite_from_selected_div = ''.join(i.rstrip() for i in div.select('.//div[@class="gs_a"]/*').re(r'^<b>(.*?)</b>(.*)'))
			# remove all the spaces, pluses, and periods from the citation so that it's just the necessary characters
			cite_from_selected_div = re.sub(r'[\+|\s|\.]', r'', cite_from_selected_div)
			# now that we have good data, see if the citation from the URL can be found in the citation from the div
			if re.search(citation_from_url, cite_from_selected_div):
				# if we have a match, grab the link that's in the div, and then request it from the site
				relurl = div.select('.//h3/a/@href').extract()
				# did the select actually capture a URL?
				if relurl == []:
					# this just stops a huge exception from popping up every time gscholar has the cite but no text
					relurl = "1"
				# pass the citation from the URL to the next function
				#	this will be the citation that's used as the key for the both_citations{} dictionary
				return Request("http://scholar.google.com" + relurl[0], callback=lambda r: self.case_page(r, citation_from_url))

	def case_page(self, response, citation_from_url):
		hxs = HtmlXPathSelector(response)

		# get the entire text of the case
		case_text = ''.join(hxs.select('//div[@id="gsl_opinion"]').extract()).encode('utf8')

		self.cursor.execute("""update cases set case_text = %s where citation like %s""", (case_text, self.both_citations[citation_from_url]))
