import scrapy

from care import settings
from care.items import Job

BASE_URL = 'https://www.care.com'
MESSAGE = '''
Hi {},

Are you ever in need of a babysitter or backup nanny on short notice?

Try our on-demand babysitting services. We guarantee a babysitter within 2 hours of your call.

All of our babysitters are:
    * Interviewed multiple times.
    * Reference checked.
    * Thoroughly background checked.

Learn more at nanniesintl.com/services/

McKenzie H.
Nannies INTL
www.nanniesintl.com
'''


class FamilySpider(scrapy.Spider):
    name = 'family_spider'
    allowed_domains = ['care.com']
    start_urls = [
        '{}/visitor/captureLogin.do'.format(BASE_URL),
    ]

    def __init__(self, zip_code=None, radius='10'):
        self.zip_code = zip_code
        self.radius = radius

    def parse(self, response):
        return scrapy.FormRequest.from_response(
            response,
            formname='smartLoginForm',
            formdata={'email': settings.CARE_EMAIL, 'password': settings.CARE_PASSWORD, 'rememberMe': 'on'},
            callback=self.search_jobs
        )

    def search_jobs(self, response):
        return scrapy.Request('https://www.care.com/visitor/captureSearchBar.do?searchPerformed=true'
                              '&sitterService=childCareJob&zipCode={}&milesFromZipCode={}'
                              '&searchByZip=true&defaultZip=true'.format(self.zip_code, self.radius),
                              callback=self.parse_jobs)

    def parse_jobs(self, response):
        page_number = response.meta['page_number'] if 'page_number' in response.meta else 1
        jobs = response.xpath('//*[contains(@class, "showJobDesignV2")]')
        results = response.xpath('//*[@id="jobSearchPagingForm"]/table/tr/td[1]/text()').extract()[0]
        total_results = results.split()[-1]
        current_results = results.split()[2]
        for i, job in enumerate(jobs):
            name = job.xpath('div[2]/div[1]/div[3]/a/text()').extract()[0].split()[0]
            applied = job.xpath('div[2]/div[2]/div[3]/div[6]/div[2]/div[1]')
            if not applied:
                job_url = '{}{}'.format(BASE_URL, job.xpath('div[2]/div[2]/div[1]/h3/a/@href').extract()[0])
                yield scrapy.Request(job_url, meta={'name': name}, callback=self.parse_job)
        if current_results != total_results:
            page_number += 1
            yield scrapy.Request(
                'https://www.care.com/visitor/captureSearchBar.do?searchPerformed=true'
                '&sitterService=childCareJob&zipCode={}&milesFromZipCode={}'
                '&searchByZip=true&defaultZip=true&pageNumber={}'.format(self.zip_code, self.radius, page_number),
                meta={'page_number': page_number},
                callback=self.parse_jobs
            )

    def parse_job(self, response):
        name = response.meta['name']
        return scrapy.FormRequest.from_response(
            response,
            formname='jobApplicationForm',
            formdata={'message': MESSAGE.format(name)},
            meta={'name': name, 'url': response.url},
            callback=self.handle_application
        )

    def handle_application(self, response):
        job = Job()
        job['name'] = response.meta['name']
        job['url'] = response.meta['url']
        return job
