import json
import locale
import logging
import pathlib
import random

from bs4 import BeautifulSoup


class ScrapeResult:
    def __init__(self, r):
        self.alert_subject = None
        self.alert_content = None
        self.price = None
        self.soup = BeautifulSoup(r.text, 'lxml')
        self.content = self.soup.body.text.lower()  # lower for case-insensitive searches
        self.url = r.url

    def __bool__(self):
        return bool(self.alert_content)

    def has_phrase(self, phrases):
        for phrase in phrases:
            if phrase in self.content:
                return True
        return False

    def set_price(self, tag):
        if not tag:
            return

        price_str = tag.text.strip()
        if not price_str:
            return

        try:
            currency_symbol = locale.localeconv()['currency_symbol']
            self.price = locale.atof(price_str.replace(currency_symbol, '').strip())
            return price_str if price_str else None
        except Exception as e:
            logging.warning(f'unable to convert "{price_str}" to float... caught exception: {e}')


class GenericScrapeResult(ScrapeResult):
    def __init__(self, r):
        super().__init__(r)

        # not perfect but usually good enough
        if self.has_phrase(['add to cart']):
            self.alert_subject = 'In Stock'
            self.alert_content = self.url


class CoolBlueScraper(ScrapeResult):

    def __init__(self, r):
        super().__init__(r)
        tags = [t.text for t in self.soup.body.findAll('button', {'class': 'button--order'})]
        has_match = any('In my shopping cart' in t for t in tags)
        if has_match:
            self.alert_subject = 'In Stock'
            self.alert_content = self.url

    def has_phrase(self, phrase):
        return False


class MediamarktScraper(ScrapeResult):

    def __init__(self, r):
        super().__init__(r)
        response = json.loads(self.content)
        is_available = any([x.get('level') != '4' for x in response.get('availabilities')])
        if is_available:
            self.alert_subject = 'In Stock'
            self.alert_content = self.url

    def has_phrase(self, phrase):
        return False


class BolScraper(ScrapeResult):

    def __init__(self, r):
        super().__init__(r)
        tags = self.soup.body.find('div', {'class': 'buy-block__title'})
        if not tags or tags.text != 'Niet leverbaar':
            self.alert_subject = 'In Stock'
            self.alert_content = self.url

    def has_phrase(self, phrase):
        return False


class IntertoysScraper(ScrapeResult):

    def __init__(self, r):
        super().__init__(r)
        sold_out_text = 'Op dit moment is de PlayStation 5 uitverkocht! Houd onze winkels en website dit najaar in de gaten voor alles over de PlayStation 5.'
        if sold_out_text.lower() not in self.content:
            self.alert_subject = 'In Stock'
            self.alert_content = self.url

    def has_phrase(self, phrase):
        return False


class GameManiaScraper(ScrapeResult):

    def __init__(self, r):
        super().__init__(r)
        is_disabled = 'lnk--button--disabled' in self.soup.body.find('div', {'class': 'lnk--addToCart'}).attrs.get(
            'class')
        if not is_disabled:
            self.alert_subject = 'In Stock'
            self.alert_content = self.url

    def has_phrase(self, phrase):
        return False


def get_result_type(url):
    if 'coolblue' in url.netloc:
        return CoolBlueScraper
    elif 'mediamarkt' in url.netloc:
        return MediamarktScraper
    elif 'bol.com' in url.netloc:
        return BolScraper
    elif 'gamemania' in url.netloc:
        return GameManiaScraper
    elif 'intertoys' in url.netloc:
        return IntertoysScraper
    return GenericScrapeResult


def get_short_name(url):
    parts = [i for i in url.path.split('/') if i]
    if parts:
        return '_'.join(parts)
    random.seed()
    return f'unknown{random.randrange(100)}'


class Scraper:
    def __init__(self, driver, url):
        self.driver = driver
        self.name = get_short_name(url)
        self.result_type = get_result_type(url)
        self.url = url
        self.in_stock_on_last_scrape = False
        self.price_on_last_scrape = None

        data_dir = pathlib.Path('data').resolve()
        data_dir.mkdir(exist_ok=True)
        self.filename = data_dir / f'{self.name}.txt'
        logging.info(f'scraper initialized for {self.url}')

    def scrape(self):
        try:
            url = str(self.url)
            r = self.driver.get(url)
            with self.filename.open('w') as f:
                f.write(r.text)
            return self.result_type(r)

        except Exception as e:
            logging.error(f'{self.name}: caught exception during request: {e}')
