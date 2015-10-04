import scrapy

from care import settings
from care.items import Sitter

BASE_URL = 'https://recruitment.care.com'
SUBJECT = 'Part Time Nanny Position'
MESSAGE = '''
Hello {},
I hope you're doing well, I was wondering if you are still looking for a nanny position? I have a part time nanny position in the Solana Beach area. The position is Monday through Thursday 6:00 am to 8:30 am and then Weds/Thurs then alternating to Thur/Fri the following week from 2:30 pm to 6:30 pm. The pay rate is $12/hr. Responsibilities would include pick up and drop offs, taking kids to activities, and helping with homework. Please let me know if this is something you might be interested in. Thank you so much, I look forward to hearing from you.

McKenzie H.
'''

class SitterSpider(scrapy.Spider):
    name = 'sitter_spider'
    allowed_domains = ['care.com']
    start_urls = [
        '{}/recruitment/visitor/login.do'.format(BASE_URL),
    ]

    def __init__(self, zip_code=None, end_page=20, start_page=1, radius='10'):
        self.zip_code = zip_code
        self.radius = radius
        self.end_page = int(end_page)
        self.start_page = start_page

    def parse(self, response):
        return scrapy.FormRequest.from_response(
            response,
            formname='recruitmentLoginForm',
            formdata={'email': settings.CARE_EMAIL, 'password': settings.CARE_PASSWORD},
            callback=self.search_sitters
        )

    def search_sitters(self, response):
        return scrapy.FormRequest.from_response(
            response,
            formname='recruitmentSitterSearchForm',
            formdata={'searchPerformed': 'true',
                      'sitterService': 'childCare',
                      'zipCodeInSession': self.zip_code,
                      'milesFromZipCode': self.radius},
            callback=self.parse_sitters)

    def parse_sitters(self, response):
        page_in_meta = 'page_number' in response.meta
        page_number = int(response.meta['page_number']) if page_in_meta else int(self.start_page)
        header = response.xpath('/html/body/div/div[1]/div[3]/div/h1/text()').extract()[0]
        total_rows = int(header.split()[2])
        total_pages = (total_rows - 10) / 15
        if page_in_meta or page_number == 1:
            sitters = response.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " result ")]')
            for i, sitter in enumerate(sitters):
                name = sitter.xpath('div[1]/div[1]/a/text()').extract()[0].split()[0]
                sitter_url = sitter.xpath('div[1]/div[1]/a/@href').extract()[0]
                yield scrapy.Request('{}{}'.format(BASE_URL, sitter_url), meta={'name': name}, callback=self.parse_sitter)
        if page_number <= self.end_page:
            if page_in_meta:
                page_number += 1
            yield scrapy.FormRequest(
                url='{}/recruitment/captureSitterSearch.do'.format(BASE_URL),
                formdata={'searchPerformed': 'true',
                          'sitterService': 'childCare',
                          'zipCodeInSession': self.zip_code,
                          'milesFromZipCode': self.radius,
                          'savedSearch': '0',
                          'hideProfiles': 'true',
                          'sortByColumn': 'distance asc',
                          'pageNumber': str(page_number),
                          'totalPages': str(total_pages),
                          'totalRows': str(total_rows),
                          'rowsPerPage': '15',
                          'showPrevious': 'false',
                          'showNext': 'true'},
                meta={'page_number': page_number},
                dont_filter=True,
                callback=self.parse_sitters
            )

    def parse_sitter(self, response):
        name = response.meta['name']
        button = response.xpath('//*[@id="three"]/div[1]/div[1]/button')
        sc = button.xpath('@sc').extract()[0]
        recipient_id = button.xpath('@recipientid').extract()[0]
        sitter_id = button.xpath('@sitterid').extract()[0]
        yield scrapy.Request(
            url='https://recruitment.care.com/ajax/uriProxy?uri=%2Frecruitment%2Fmember%2FsendMessageDialog.do%3F'
                'recipientId%3D{recipient_id}%26sc%3D{sc}%26serviceId%3DCHILDCARE%26sitterId%3D{sitter_id}%26tabId%3D'
                'contactDetails'.format(recipient_id=recipient_id, sc=sc, sitter_id=sitter_id),
            meta={'name': name, 'sc': sc, 'sitter_id': sitter_id, 'url': response.url},
            callback=self.send_message
        )

    def send_message(self, response):
        name = response.meta['name']
        yield scrapy.FormRequest(
            url='{}/recruitment/member/captureSendMessageDialog.do'.format(BASE_URL),
            formdata={'subject': SUBJECT,
                      'message': MESSAGE.format(name),
                      'recipientId': response.meta['sitter_id'],
                      'sc': response.meta['sc']},
            meta={'name': name, 'url': response.meta['url']},
            dont_filter=True,
            callback=self.handle_message
        )

    def handle_message(self, response):
        sitter = Sitter()
        sitter['name'] = response.meta['name']
        sitter['url'] = response.meta['url']
        return sitter
