from logbook import Logger
from six.moves import urllib
import json
import pandas as pd

from catalyst.exchange.exchange import Exchange
from catalyst.exchange.bittrex.bittrex_api import Bittrex_api

log = Logger('Bittrex')


class Bittrex(Exchange):
    def __init__(self, key, secret, base_currency, portfolio=None):
        self.api = Bittrex_api(key=key, secret=secret)
        self.name = 'bittrex'

        self.assets = dict()
        self.load_assets()

    @property
    def account(self):
        pass

    @property
    def portfolio(self):
        pass

    @property
    def positions(self):
        pass

    @property
    def time_skew(self):
        pass

    def sanitize_curency_symbol(self, exchange_symbol):
        """
        Helper method used to build the universal pair.
        Include any symbol mapping here if appropriate.

        :param exchange_symbol:
        :return universal_symbol:
        """
        return exchange_symbol.lower()

    def fetch_symbol_map(self):
        """
        Since Bittrex gives us a complete dictionary of symbols,
        we can build the symbol map ad-hoc as opposed to maintaining
        a static file. We must be careful with mapping any unconventional
        symbol name as appropriate.

        :return symbol_map:
        """
        symbol_map = dict()

        markets = self.api.getmarkets()
        for market in markets:
            exchange_symbol = market['MarketName']
            symbol = '{market}_{base}'.format(
                market=self.sanitize_curency_symbol(market['MarketCurrency']),
                base=self.sanitize_curency_symbol(market['BaseCurrency'])
            )
            symbol_map[exchange_symbol] = dict(
                symbol=symbol,
                start_date=pd.to_datetime(market['Created'], utc=True)
            )

        return symbol_map

    def update_portfolio(self):
        pass

    def order(self):
        log.info('creating order')
        pass

    def get_open_orders(self, asset):
        pass

    def open_orders(self):
        log.info('retrieving open orders')
        pass

    def get_order(self):
        log.info('retrieving order')
        pass

    def cancel_order(self):
        log.info('cancel order')
        pass

    def get_candles(self):
        log.info('retrieving candles')
        url = 'https://bittrex.com/Api/v2.0/pub/market/GetTicks?marketName=BTC-NEO&tickInterval=day&_=1499127220008'
        with urllib.request.urlopen(url) as url:
            data = json.loads(url.read().decode())
            result = data['result']
        pass

    def tickers(self):
        log.info('retrieving tickers')
        pass

    def get_account(self):
        log.info('retrieving account data')
        pass
