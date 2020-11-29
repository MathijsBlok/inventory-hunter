import getpass
import logging
import os

import requests
from selenium import webdriver


class HttpGetResponse:
    def __init__(self, text, url):
        self.text = text
        self.url = url


class SeleniumDriver:
    def __init__(self, timeout):
        self.timeout = timeout
        self.init()

    def init(self):
        self.driver = None

        driver_path = '/usr/bin/chromedriver'
        if not os.path.exists(driver_path):
            raise Exception(f'not found: {driver_path}')

        options = webdriver.ChromeOptions()
        options.headless = True
        if getpass.getuser() == 'root':
            options.add_argument('--no-sandbox')  # required if root

        self.driver = webdriver.Chrome(driver_path, options=options)
        self.driver.implicitly_wait(self.timeout)

    def __del__(self):
        if self.driver is not None:
            self.driver.quit()

    def get(self, url):
        try:
            self.driver.get(url)
        except Exception as e:
            logging.error(f'Exception during request: {e}')
            self.init()

        return HttpGetResponse(self.driver.page_source, url)


class RequestsDriver:
    def __init__(self, timeout):
        self.timeout = timeout

    def get(self, url):
        r = requests.get(url, timeout=self.timeout)
        if not r.ok:
            raise Exception(f'got response with status code {r.status_code} for {url}')
        return HttpGetResponse(r.text, r.url)


def init_driver(config):
    timeout = config.refresh_interval
    try:
        return SeleniumDriver(timeout)
    except Exception as e:
        logging.error(f'caught exception during selenium driver init: {e}')
        logging.warning('falling back to requests module')
        return RequestsDriver(timeout)
