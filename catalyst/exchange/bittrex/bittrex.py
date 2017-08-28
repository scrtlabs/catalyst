from catalyst.exchange.exchange_errors import InvalidHistoryFrequencyError, \
    ExchangeRequestError
from logbook import Logger
from six.moves import urllib
import json
import pandas as pd

from catalyst.exchange.exchange import Exchange
from catalyst.exchange.bittrex.bittrex_api import Bittrex_api
from catalyst.assets._assets import TradingPair

log = Logger('Bittrex')

URL2 = 'https://bittrex.com/Api/v2.0'


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

    def create_order(self, asset, amount, is_buy, style):
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

    def get_candles(self, data_frequency, assets, bar_count=None):
        """

        Supported Intervals
        -------------------
        day, oneMin, fiveMin, thirtyMin, hour
        :param data_frequency:
        :param assets:
        :param bar_count:
        :return:
        """
        log.info('retrieving candles')
        if data_frequency == 'minute' or data_frequency == '1m':
            frequency = 'oneMin'
        elif data_frequency == '5m':
            frequency = 'fiveMin'
        elif data_frequency == '30m':
            frequency = 'thirtyMin'
        elif data_frequency == '1h':
            frequency = 'hour'
        elif data_frequency == 'daily' or data_frequency == '1D':
            frequency = 'day'
        else:
            raise InvalidHistoryFrequencyError(
                frequency=data_frequency
            )

        # Making sure that assets are iterable
        asset_list = [assets] if isinstance(assets, TradingPair) else assets
        ohlc_map = dict()
        for asset in asset_list:
            url = '{url}/pub/market/GetTicks?marketName={symbol}' \
                  '&tickInterval={frequency}&_=1499127220008'.format(
                url=URL2,
                symbol=self.get_symbol(asset),
                frequency=frequency
            )

            try:
                data = json.loads(urllib.request.urlopen(url).read().decode())
            except Exception as e:
                raise ExchangeRequestError(error=e)

            if data['message']:
                raise ExchangeRequestError(
                    error='Unable to fetch candles {}'.format(data['message'])
                )

            candles = data['result']

            def ohlc_from_candle(candle):
                ohlc = dict(
                    open=candle['O'],
                    high=candle['H'],
                    low=candle['L'],
                    close=candle['C'],
                    volume=candle['V'],
                    price=candle['C'],
                    last_traded=pd.to_datetime(candle['T'], utc=True)
                )
                return ohlc

            ordered_candles = list(reversed(candles))
            if bar_count is None:
                ohlc_map[asset] = ohlc_from_candle(ordered_candles[-1])
            else:
                ohlc_bars = []
                for candle in ordered_candles[:bar_count]:
                    ohlc = ohlc_from_candle(candle)
                    ohlc_bars.append(ohlc)

                ohlc_map[asset] = ohlc_bars

        return ohlc_map[assets] \
            if isinstance(assets, TradingPair) else ohlc_map

    def tickers(self):
        log.info('retrieving tickers')
        pass

    def get_account(self):
        log.info('retrieving account data')
        pass
