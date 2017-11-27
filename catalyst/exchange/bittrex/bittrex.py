import json
import time

import pandas as pd
from catalyst.assets._assets import TradingPair
from logbook import Logger
from six.moves import urllib

from catalyst.constants import LOG_LEVEL
from catalyst.exchange.bittrex.bittrex_api import Bittrex_api
from catalyst.exchange.exchange import Exchange
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.exchange_errors import InvalidHistoryFrequencyError, \
    ExchangeRequestError, InvalidOrderStyle, OrderNotFound, OrderCancelError, \
    CreateOrderError
from catalyst.exchange.exchange_utils import get_exchange_symbols_filename, \
    download_exchange_symbols, get_symbols_string
from catalyst.finance.execution import LimitOrder, StopLimitOrder
from catalyst.finance.order import Order, ORDER_STATUS

# TODO: consider using this: https://github.com/mondeja/bittrex_v2

log = Logger('Bittrex', level=LOG_LEVEL)

URL2 = 'https://bittrex.com/Api/v2.0'


class Bittrex(Exchange):
    def __init__(self, key, secret, base_currency, portfolio=None):
        self.api = Bittrex_api(key=key, secret=secret)
        self.name = 'bittrex'
        self.color = 'blue'
        self.base_currency = base_currency
        self._portfolio = portfolio

        self.num_candles_limit = 2000

        # Not sure what the rate limit is but trying to play it safe
        # https://bitcoin.stackexchange.com/questions/53778/bittrex-api-rate-limit
        self.max_requests_per_minute = 60
        self.request_cpt = dict()

        self.minute_writer = None
        self.minute_reader = None

        self.assets = dict()
        self.load_assets()

        self.local_assets = dict()
        self.load_assets(is_local=True)

        self.bundle = ExchangeBundle(self.name)

    @property
    def account(self):
        pass

    @property
    def time_skew(self):
        # TODO: research the time skew conditions
        return pd.Timedelta('0s')

    def sanitize_curency_symbol(self, exchange_symbol):
        """
        Helper method used to build the universal pair.
        Include any symbol mapping here if appropriate.

        :param exchange_symbol:
        :return universal_symbol:
        """
        return exchange_symbol.lower()

    def get_balances(self):
        balances = self.api.getbalances()
        try:
            log.debug('retrieving wallet balances')
            self.ask_request()

        except Exception as e:
            raise ExchangeRequestError(error=e)

        std_balances = dict()
        try:
            for balance in balances:
                currency = balance['Currency'].lower()
                std_balances[currency] = balance['Available']

        except TypeError:
            raise ExchangeRequestError(error=balances)

        return std_balances

    def create_order(self, asset, amount, is_buy, style):
        log.info('creating {} order'.format('buy' if is_buy else 'sell'))
        exchange_symbol = self.get_symbol(asset)

        if isinstance(style, LimitOrder) or isinstance(style, StopLimitOrder):
            if isinstance(style, StopLimitOrder):
                log.warn('{} will ignore the stop price'.format(self.name))

            price = style.get_limit_price(is_buy)
            try:
                self.ask_request()
                if is_buy:
                    order_status = self.api.buylimit(exchange_symbol, amount,
                                                     price)
                else:
                    order_status = self.api.selllimit(exchange_symbol,
                                                      abs(amount), price)
            except Exception as e:
                raise ExchangeRequestError(error=e)

            if 'uuid' in order_status:
                order_id = order_status['uuid']
                order = Order(
                    dt=pd.Timestamp.utcnow(),
                    asset=asset,
                    amount=amount,
                    stop=style.get_stop_price(is_buy),
                    limit=style.get_limit_price(is_buy),
                    id=order_id
                )
                return order
            else:
                if order_status == 'INSUFFICIENT_FUNDS':
                    log.warn('not enough funds to create order')
                    return None
                elif order_status == 'DUST_TRADE_DISALLOWED_MIN_VALUE_50K_SAT':
                    log.warn('Your order is too small, order at least 50K'
                             ' Satoshi')
                    return None
                else:
                    raise CreateOrderError(
                        exchange=self.name,
                        error=order_status
                    )
        else:
            raise InvalidOrderStyle(exchange=self.name,
                                    style=style.__class__.__name__)

    def get_open_orders(self, asset):
        symbol = self.get_symbol(asset)
        try:
            self.ask_request()
            open_orders = self.api.getopenorders(symbol)
        except Exception as e:
            raise ExchangeRequestError(error=e)

        orders = list()
        for order_status in open_orders:
            order = self._create_order(order_status)
            orders.append(order)

        return orders

    def _create_order(self, order_status):
        log.info(
            'creating catalyst order from Bittrex {}'.format(order_status))
        if order_status['CancelInitiated']:
            status = ORDER_STATUS.CANCELLED
        elif order_status['Closed'] is not None:
            status = ORDER_STATUS.FILLED
        else:
            status = ORDER_STATUS.OPEN

        date = pd.to_datetime(order_status['Opened'], utc=True)
        amount = order_status['Quantity']
        filled = amount - order_status['QuantityRemaining']
        order = Order(
            dt=date,
            asset=self.assets[order_status['Exchange']],
            amount=amount,
            stop=None,  # Not yet supported by Bittrex
            limit=order_status['Limit'],
            filled=filled,
            id=order_status['OrderUuid'],
            commission=order_status['CommissionPaid']
        )
        order.status = status

        executed_price = order_status['PricePerUnit']

        return order, executed_price

    def get_order(self, order_id):
        log.info('retrieving order {}'.format(order_id))
        try:
            self.ask_request()
            order_status = self.api.getorder(order_id)
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if order_status is None:
            raise OrderNotFound(order_id=order_id, exchange=self.name)

        return self._create_order(order_status)

    def cancel_order(self, order_param):
        order_id = order_param.id \
            if isinstance(order_param, Order) else order_param
        log.info('cancelling order {}'.format(order_id))

        try:
            self.ask_request()
            status = self.api.cancel(order_id)
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if 'message' in status:
            raise OrderCancelError(
                order_id=order_id,
                exchange=self.name,
                error=status['message']
            )

    def get_candles(self, freq, assets, bar_count=None,
                    start_dt=None, end_dt=None):
        """
        Supported Intervals
        -------------------
        day, oneMin, fiveMin, thirtyMin, hour

        :param freq:
        :param assets:
        :param bar_count:
        :param start_dt
        :param end_dt
        :return:
        """

        # TODO: this has no effect at the moment
        if end_dt is None:
            end_dt = pd.Timestamp.utcnow()

        log.debug(
            'retrieving {bars} {freq} candles on {exchange} from '
            '{end_dt} for markets {symbols}, '.format(
                bars=bar_count,
                freq=freq,
                exchange=self.name,
                end_dt=end_dt,
                symbols=get_symbols_string(assets)
            )
        )

        if freq == '1T':
            frequency = 'oneMin'
        elif freq == '5T':
            frequency = 'fiveMin'
        elif freq == '30T':
            frequency = 'thirtyMin'
        elif freq == '60T':
            frequency = 'hour'
        elif freq == '1D':
            frequency = 'day'
        else:
            raise InvalidHistoryFrequencyError(frequency=freq)

        # Making sure that assets are iterable
        asset_list = [assets] if isinstance(assets, TradingPair) else assets
        for asset in asset_list:
            end = int(time.mktime(end_dt.timetuple()))
            url = '{url}/pub/market/GetTicks?marketName={symbol}' \
                  '&tickInterval={frequency}&_={end}'.format(
                url=URL2,
                symbol=self.get_symbol(asset),
                frequency=frequency,
                end=end
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
            ohlc_map = dict()
            if bar_count is None:
                ohlc_map[asset] = ohlc_from_candle(ordered_candles[0])
            else:
                # TODO: optimize
                ohlc_bars = []
                for candle in ordered_candles[:bar_count]:
                    ohlc = ohlc_from_candle(candle)
                    ohlc_bars.append(ohlc)

                ohlc_map[asset] = ohlc_bars

        return ohlc_map[assets] \
            if isinstance(assets, TradingPair) else ohlc_map

    def tickers(self, assets):
        """
        As of v1.1, Bittrex only allows one ticker at the time.
        So we have to make multiple calls to fetch multiple assets.

        :param assets:
        :return:
        """
        log.info('retrieving tickers')

        ticks = dict()
        for asset in assets:
            symbol = self.get_symbol(asset)
            try:
                self.ask_request()
                ticker = self.api.getticker(symbol)
            except Exception as e:
                raise ExchangeRequestError(error=e)

            # TODO: catch invalid ticker
            ticks[asset] = dict(
                timestamp=pd.Timestamp.utcnow(),
                bid=ticker['Bid'],
                ask=ticker['Ask'],
                last_price=ticker['Last']
            )

        log.debug('got tickers {}'.format(ticks))
        return ticks

    def get_account(self):
        log.info('retrieving account data')
        pass

    def generate_symbols_json(self, filename=None):
        symbol_map = {}

        fn, r = download_exchange_symbols(self.name)
        with open(fn) as data_file:
            cached_symbols = json.load(data_file)

        markets = self.api.getmarkets()
        for market in markets:
            exchange_symbol = market['MarketName']
            symbol = '{market}_{base}'.format(
                market=self.sanitize_curency_symbol(market['MarketCurrency']),
                base=self.sanitize_curency_symbol(market['BaseCurrency'])
            )

            try:
                end_daily = cached_symbols[exchange_symbol]['end_daily']
            except KeyError as e:
                end_daily = 'N/A'

            try:
                end_minute = cached_symbols[exchange_symbol]['end_minute']
            except KeyError as e:
                end_minute = 'N/A'

            symbol_map[exchange_symbol] = dict(
                symbol=symbol,
                start_date=pd.to_datetime(market['Created'],
                                          utc=True).strftime("%Y-%m-%d"),
                end_daily=end_daily,
                end_minute=end_minute,
            )

        if (filename is None):
            filename = get_exchange_symbols_filename(self.name)

        with open(filename, 'w') as f:
            json.dump(symbol_map, f, sort_keys=True, indent=2,
                      separators=(',', ':'))

    def get_orderbook(self, asset, order_type='all', limit=100):
        if order_type == 'all':
            order_type = 'both'
        elif order_type == 'bid':
            order_type = 'buy'
        elif order_type == 'ask':
            order_type = 'sell'
        else:
            raise ValueError('invalid type')

        exchange_symbol = asset.exchange_symbol
        data = self.api.getorderbook(
            market=exchange_symbol,
            type=order_type,
            depth=100
        )

        result = dict()
        for exchange_type in data:
            if exchange_type == 'buy':
                order_type = 'bids'
            elif exchange_type == 'sell':
                order_type = 'asks'

            result[order_type] = []
            for entry in data[exchange_type]:
                result[order_type].append(dict(
                    rate=entry['Rate'],
                    quantity=entry['Quantity']
                ))

        return result
