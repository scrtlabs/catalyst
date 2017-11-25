import base64
import datetime
import hashlib
import hmac
import json
import re
import time

import numpy as np
import pandas as pd
import pytz
import requests
import six
from catalyst.assets._assets import TradingPair
from logbook import Logger

from catalyst.exchange.exchange import Exchange
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.exchange_errors import (
    ExchangeRequestError,
    InvalidHistoryFrequencyError,
    InvalidOrderStyle, OrderCancelError)
from catalyst.exchange.exchange_execution import ExchangeLimitOrder, \
    ExchangeStopLimitOrder, ExchangeStopOrder
from catalyst.exchange.exchange_utils import get_exchange_symbols_filename, \
    download_exchange_symbols, get_symbols_string
from catalyst.finance.order import Order, ORDER_STATUS
from catalyst.protocol import Account

# Trying to account for REST api instability
# https://stackoverflow.com/questions/15431044/can-i-set-max-retries-for-requests-request
requests.adapters.DEFAULT_RETRIES = 20

BITFINEX_URL = 'https://api.bitfinex.com'

from catalyst.constants import LOG_LEVEL

log = Logger('Bitfinex', level=LOG_LEVEL)
warning_logger = Logger('AlgoWarning')


class Bitfinex(Exchange):
    def __init__(self, key, secret, base_currency, portfolio=None):
        self.url = BITFINEX_URL
        self.key = key
        self.secret = secret.encode('UTF-8')
        self.name = 'bitfinex'
        self.color = 'green'

        self.assets = dict()
        self.load_assets()

        self.local_assets = dict()
        self.load_assets(is_local=True)

        self.base_currency = base_currency
        self._portfolio = portfolio
        self.minute_writer = None
        self.minute_reader = None

        # The candle limit for each request
        self.num_candles_limit = 1000

        # Max is 90 but playing it safe
        # https://www.bitfinex.com/posts/188
        self.max_requests_per_minute = 80
        self.request_cpt = dict()

        self.bundle = ExchangeBundle(self.name)

    def _request(self, operation, data, version='v1'):
        payload_object = {
            'request': '/{}/{}'.format(version, operation),
            'nonce': '{0:f}'.format(time.time() * 1000000),
            # convert to string
            'options': {}
        }

        if data is None:
            payload_dict = payload_object
        else:
            payload_dict = payload_object.copy()
            payload_dict.update(data)

        payload_json = json.dumps(payload_dict)
        if six.PY3:
            payload = base64.b64encode(bytes(payload_json, 'utf-8'))
        else:
            payload = base64.b64encode(payload_json)

        m = hmac.new(self.secret, payload, hashlib.sha384)
        m = m.hexdigest()

        # headers
        headers = {
            'X-BFX-APIKEY': self.key,
            'X-BFX-PAYLOAD': payload,
            'X-BFX-SIGNATURE': m
        }

        if data is None:
            request = requests.get(
                '{url}/{version}/{operation}'.format(
                    url=self.url,
                    version=version,
                    operation=operation
                ), data={},
                headers=headers)
        else:
            request = requests.post(
                '{url}/{version}/{operation}'.format(
                    url=self.url,
                    version=version,
                    operation=operation
                ),
                headers=headers)

        return request

    def _get_v2_symbol(self, asset):
        pair = asset.symbol.split('_')
        symbol = 't' + pair[0].upper() + pair[1].upper()
        return symbol

    def _get_v2_symbols(self, assets):
        """
        Workaround to support Bitfinex v2
        TODO: Might require a separate asset dictionary

        :param assets:
        :return:
        """

        v2_symbols = []
        for asset in assets:
            v2_symbols.append(self._get_v2_symbol(asset))

        return v2_symbols

    def _create_order(self, order_status):
        """
        Create a Catalyst order object from a Bitfinex order dictionary
        :param order_status:
        :return: Order
        """
        if order_status['is_cancelled']:
            status = ORDER_STATUS.CANCELLED
        elif not order_status['is_live']:
            log.info('found executed order {}'.format(order_status))
            status = ORDER_STATUS.FILLED
        else:
            status = ORDER_STATUS.OPEN

        amount = float(order_status['original_amount'])
        filled = float(order_status['executed_amount'])

        if order_status['side'] == 'sell':
            amount = -amount
            filled = -filled

        price = float(order_status['price'])
        order_type = order_status['type']

        stop_price = None
        limit_price = None

        # TODO: is this comprehensive enough?
        if order_type.endswith('limit'):
            limit_price = price
        elif order_type.endswith('stop'):
            stop_price = price

        executed_price = float(order_status['avg_execution_price'])

        # TODO: bitfinex does not specify comission. I could calculate it but not sure if it's worth it.
        commission = None

        date = pd.Timestamp.utcfromtimestamp(float(order_status['timestamp']))
        date = pytz.utc.localize(date)
        order = Order(
            dt=date,
            asset=self.assets[order_status['symbol']],
            amount=amount,
            stop=stop_price,
            limit=limit_price,
            filled=filled,
            id=str(order_status['id']),
            commission=commission
        )
        order.status = status

        return order, executed_price

    def get_balances(self):
        log.debug('retrieving wallets balances')
        try:
            self.ask_request()
            response = self._request('balances', None)
            balances = response.json()
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if 'message' in balances:
            raise ExchangeRequestError(
                error='unable to fetch balance {}'.format(balances['message'])
            )

        std_balances = dict()
        for balance in balances:
            currency = balance['currency'].lower()
            std_balances[currency] = float(balance['available'])

        return std_balances

    @property
    def account(self):
        account = Account()

        account.settled_cash = None
        account.accrued_interest = None
        account.buying_power = None
        account.equity_with_loan = None
        account.total_positions_value = None
        account.total_positions_exposure = None
        account.regt_equity = None
        account.regt_margin = None
        account.initial_margin_requirement = None
        account.maintenance_margin_requirement = None
        account.available_funds = None
        account.excess_liquidity = None
        account.cushion = None
        account.day_trades_remaining = None
        account.leverage = None
        account.net_leverage = None
        account.net_liquidation = None

        return account

    @property
    def time_skew(self):
        # TODO: research the time skew conditions
        return pd.Timedelta('0s')

    def get_account(self):
        # TODO: fetch account data and keep in cache
        return None

    def get_candles(self, freq, assets, bar_count=None,
                    start_dt=None, end_dt=None):
        """
        Retrieve OHLVC candles from Bitfinex

        :param data_frequency:
        :param assets:
        :param bar_count:
        :return:

        Available Frequencies
        ---------------------
        '1m', '5m', '15m', '30m', '1h', '3h', '6h', '12h', '1D', '7D', '14D',
         '1M'
        """
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

        allowed_frequencies = ['1T', '5T', '15T', '30T', '60T', '180T',
                               '360T', '720T', '1D', '7D', '14D', '30D']
        if freq not in allowed_frequencies:
            raise InvalidHistoryFrequencyError(frequency=freq)

        freq_match = re.match(r'([0-9].*)(T|H|D)', freq, re.M | re.I)
        if freq_match:
            number = int(freq_match.group(1))
            unit = freq_match.group(2)

            if unit == 'T':
                if number in [60, 180, 360, 720]:
                    number = number / 60
                    converted_unit = 'h'
                else:
                    converted_unit = 'm'
            else:
                converted_unit = unit

            frequency = '{}{}'.format(number, converted_unit)

        else:
            raise InvalidHistoryFrequencyError(frequency=freq)

        # Making sure that assets are iterable
        asset_list = [assets] if isinstance(assets, TradingPair) else assets
        ohlc_map = dict()
        for asset in asset_list:
            symbol = self._get_v2_symbol(asset)
            url = '{url}/v2/candles/trade:{frequency}:{symbol}'.format(
                url=self.url,
                frequency=frequency,
                symbol=symbol
            )

            if bar_count:
                is_list = True
                url += '/hist?limit={}'.format(int(bar_count))

                def get_ms(date):
                    epoch = datetime.datetime.utcfromtimestamp(0)
                    epoch = epoch.replace(tzinfo=pytz.UTC)

                    return (date - epoch).total_seconds() * 1000.0

                if start_dt is not None:
                    start_ms = get_ms(start_dt)
                    url += '&start={0:f}'.format(start_ms)

                if end_dt is not None:
                    end_ms = get_ms(end_dt)
                    url += '&end={0:f}'.format(end_ms)

            else:
                is_list = False
                url += '/last'

            try:
                self.ask_request()
                response = requests.get(url)
            except Exception as e:
                raise ExchangeRequestError(error=e)

            if 'error' in response.content:
                raise ExchangeRequestError(
                    error='Unable to retrieve candles: {}'.format(
                        response.content)
                )

            candles = response.json()

            def ohlc_from_candle(candle):
                last_traded = pd.Timestamp.utcfromtimestamp(
                    candle[0] / 1000.0)
                last_traded = last_traded.replace(tzinfo=pytz.UTC)
                ohlc = dict(
                    open=np.float64(candle[1]),
                    high=np.float64(candle[3]),
                    low=np.float64(candle[4]),
                    close=np.float64(candle[2]),
                    volume=np.float64(candle[5]),
                    price=np.float64(candle[2]),
                    last_traded=last_traded
                )
                return ohlc

            if is_list:
                ohlc_bars = []
                # We can to list candles from old to new
                for candle in reversed(candles):
                    ohlc = ohlc_from_candle(candle)
                    ohlc_bars.append(ohlc)

                ohlc_map[asset] = ohlc_bars

            else:
                ohlc = ohlc_from_candle(candles)
                ohlc_map[asset] = ohlc

        return ohlc_map[assets] \
            if isinstance(assets, TradingPair) else ohlc_map

    def create_order(self, asset, amount, is_buy, style):
        """
        Creating order on the exchange.

        :param asset:
        :param amount:
        :param is_buy:
        :param style:
        :return:
        """
        exchange_symbol = self.get_symbol(asset)
        if isinstance(style, ExchangeLimitOrder) \
                or isinstance(style, ExchangeStopLimitOrder):
            price = style.get_limit_price(is_buy)
            order_type = 'limit'

        elif isinstance(style, ExchangeStopOrder):
            price = style.get_stop_price(is_buy)
            order_type = 'stop'

        else:
            raise InvalidOrderStyle(exchange=self.name,
                                    style=style.__class__.__name__)

        req = dict(
            symbol=exchange_symbol,
            amount=str(float(abs(amount))),
            price="{:.20f}".format(float(price)),
            side='buy' if is_buy else 'sell',
            type='exchange ' + order_type,  # TODO: support margin trades
            exchange=self.name,
            is_hidden=False,
            is_postonly=False,
            use_all_available=0,
            ocoorder=False,
            buy_price_oco=0,
            sell_price_oco=0
        )

        date = pd.Timestamp.utcnow()
        try:
            self.ask_request()
            response = self._request('order/new', req)
            order_status = response.json()
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if 'message' in order_status:
            raise ExchangeRequestError(
                error='unable to create Bitfinex order {}'.format(
                    order_status['message'])
            )

        order_id = str(order_status['id'])
        order = Order(
            dt=date,
            asset=asset,
            amount=amount,
            stop=style.get_stop_price(is_buy),
            limit=style.get_limit_price(is_buy),
            id=order_id
        )

        return order

    def get_open_orders(self, asset=None):
        """Retrieve all of the current open orders.

        Parameters
        ----------
        asset : Asset
            If passed and not None, return only the open orders for the given
            asset instead of all open orders.

        Returns
        -------
        open_orders : dict[list[Order]] or list[Order]
            If no asset is passed this will return a dict mapping Assets
            to a list containing all the open orders for the asset.
            If an asset is passed then this will return a list of the open
            orders for this asset.
        """
        try:
            self.ask_request()
            response = self._request('orders', None)
            order_statuses = response.json()
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if 'message' in order_statuses:
            raise ExchangeRequestError(
                error='Unable to retrieve open orders: {}'.format(
                    order_statuses['message'])
            )

        orders = []
        for order_status in order_statuses:
            order, executed_price = self._create_order(order_status)
            if asset is None or asset == order.sid:
                orders.append(order)

        return orders

    def get_order(self, order_id):
        """Lookup an order based on the order id returned from one of the
        order functions.

        Parameters
        ----------
        order_id : str
            The unique identifier for the order.

        Returns
        -------
        order : Order
            The order object.
        """
        try:
            self.ask_request()
            response = self._request(
                'order/status', {'order_id': int(order_id)})
            order_status = response.json()
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if 'message' in order_status:
            raise ExchangeRequestError(
                error='Unable to retrieve order status: {}'.format(
                    order_status['message'])
            )
        return self._create_order(order_status)

    def cancel_order(self, order_param):
        """Cancel an open order.

        Parameters
        ----------
        order_param : str or Order
            The order_id or order object to cancel.
        """
        order_id = order_param.id \
            if isinstance(order_param, Order) else order_param

        try:
            self.ask_request()
            response = self._request('order/cancel', {'order_id': order_id})
            status = response.json()
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if 'message' in status:
            raise OrderCancelError(
                order_id=order_id,
                exchange=self.name,
                error=status['message']
            )

    def tickers(self, assets):
        """
        Fetch ticket data for assets
        https://docs.bitfinex.com/v2/reference#rest-public-tickers

        :param assets:
        :return:
        """
        symbols = self._get_v2_symbols(assets)
        log.debug('fetching tickers {}'.format(symbols))

        try:
            self.ask_request()
            response = requests.get(
                '{url}/v2/tickers?symbols={symbols}'.format(
                    url=self.url,
                    symbols=','.join(symbols),
                )
            )
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if 'error' in response.content:
            raise ExchangeRequestError(
                error='Unable to retrieve tickers: {}'.format(
                    response.content)
            )

        try:
            tickers = response.json()
        except Exception as e:
            raise ExchangeRequestError(error=e)

        ticks = dict()
        for index, ticker in enumerate(tickers):
            if not len(ticker) == 11:
                raise ExchangeRequestError(
                    error='Invalid ticker in response: {}'.format(ticker)
                )

            ticks[assets[index]] = dict(
                timestamp=pd.Timestamp.utcnow(),
                bid=ticker[1],
                ask=ticker[3],
                last_price=ticker[7],
                low=ticker[10],
                high=ticker[9],
                volume=ticker[8],
            )

        log.debug('got tickers {}'.format(ticks))
        return ticks

    def generate_symbols_json(self, filename=None, source_dates=False):
        symbol_map = {}

        if not source_dates:
            fn, r = download_exchange_symbols(self.name)
            with open(fn) as data_file:
                cached_symbols = json.load(data_file)

        response = self._request('symbols', None)

        for symbol in response.json():
            if (source_dates):
                start_date = self.get_symbol_start_date(symbol)
            else:
                try:
                    start_date = cached_symbols[symbol]['start_date']
                except KeyError as e:
                    start_date = time.strftime('%Y-%m-%d')

            try:
                end_daily = cached_symbols[symbol]['end_daily']
            except KeyError as e:
                end_daily = 'N/A'

            try:
                end_minute = cached_symbols[symbol]['end_minute']
            except KeyError as e:
                end_minute = 'N/A'

            symbol_map[symbol] = dict(
                symbol=symbol[:-3] + '_' + symbol[-3:],
                start_date=start_date,
                end_daily=end_daily,
                end_minute=end_minute,
            )

        if (filename is None):
            filename = get_exchange_symbols_filename(self.name)

        with open(filename, 'w') as f:
            json.dump(symbol_map, f, sort_keys=True, indent=2,
                      separators=(',', ':'))

    def get_symbol_start_date(self, symbol):

        print(symbol)
        symbol_v2 = 't' + symbol.upper()

        """
            For each symbol we retrieve candles with Monhtly resolution
            We get the first month, and query again with daily resolution
            around that date, and we get the first date
        """
        url = '{url}/v2/candles/trade:1M:{symbol}/hist'.format(
            url=self.url,
            symbol=symbol_v2
        )

        try:
            self.ask_request()
            response = requests.get(url)
        except Exception as e:
            raise ExchangeRequestError(error=e)

        """
            If we don't get any data back for our monthly-resolution query
            it means that symbol started trading less than a month ago, so
            arbitrarily set the ref. date to 15 days ago to be safe with
            +/- 31 days
        """
        if (len(response.json())):
            startmonth = response.json()[-1][0]
        else:
            startmonth = int((time.time() - 15 * 24 * 3600) * 1000)

        """
            Query again with daily resolution setting the start and end around
            the startmonth we got above. Avoid end dates greater than now: time.time()
        """
        url = '{url}/v2/candles/trade:1D:{symbol}/hist?start={start}&end={end}'.format(
            url=self.url,
            symbol=symbol_v2,
            start=startmonth - 3600 * 24 * 31 * 1000,
            end=min(startmonth + 3600 * 24 * 31 * 1000,
                    int(time.time() * 1000))
        )

        try:
            self.ask_request()
            response = requests.get(url)
        except Exception as e:
            raise ExchangeRequestError(error=e)

        return time.strftime('%Y-%m-%d',
                             time.gmtime(int(response.json()[-1][0] / 1000)))

    def get_orderbook(self, asset, order_type='all', limit=100):
        exchange_symbol = asset.exchange_symbol
        try:
            self.ask_request()
            # TODO: implement limit
            response = self._request(
                'book/{}'.format(exchange_symbol), None)
            data = response.json()

        except Exception as e:
            raise ExchangeRequestError(error=e)

        # TODO: filter by type
        result = dict()
        for order_type in data:
            result[order_type] = []

            for entry in data[order_type]:
                result[order_type].append(dict(
                    rate=float(entry['price']),
                    quantity=float(entry['amount'])
                ))

        return result
