import base64
import hashlib
import hmac
import json
import re
import time

import numpy as np
import pandas as pd
import pytz
import requests
#import six
from six import iteritems
from catalyst.assets._assets import TradingPair
from logbook import Logger

from catalyst.exchange.poloniex.poloniex_api import Poloniex_api


# from websocket import create_connection
from catalyst.exchange.exchange import Exchange
from catalyst.exchange.exchange_errors import (
    ExchangeRequestError,
    InvalidHistoryFrequencyError,
    InvalidOrderStyle, OrderCancelError)
from catalyst.exchange.exchange_execution import ExchangeLimitOrder, \
    ExchangeStopLimitOrder, ExchangeStopOrder
from catalyst.finance.order import Order, ORDER_STATUS
from catalyst.protocol import Account
from catalyst.exchange.exchange_utils import get_exchange_symbols_filename


log = Logger('Poloniex')


class Poloniex(Exchange):
    def __init__(self, key, secret, base_currency, portfolio=None):
        self.api = Poloniex_api(key=key, secret=secret.encode('UTF-8'))
        self.name = 'poloniex'
        self.assets = {}
        self.load_assets()
        self.base_currency = base_currency
        self._portfolio = portfolio
        self.minute_writer = None
        self.minute_reader = None


    def sanitize_curency_symbol(self, exchange_symbol):
        """
        Helper method used to build the universal pair.
        Include any symbol mapping here if appropriate.

        :param exchange_symbol:
        :return universal_symbol:
        """
        return exchange_symbol.lower()

    
    def _create_order(self, order_status):
        """
        Create a Catalyst order object from the Exchange order dictionary
        :param order_status:
        :return: Order
        """
        #if order_status['is_cancelled']:
        #    status = ORDER_STATUS.CANCELLED
        #elif not order_status['is_live']:
        #    log.info('found executed order {}'.format(order_status))
        #    status = ORDER_STATUS.FILLED
        #else:
        status = ORDER_STATUS.OPEN

        amount = float(order_status['amount'])
        #filled = float(order_status['executed_amount'])
        filled = None

        if order_status['type'] == 'sell':
            amount = -amount
            #filled = -filled

        price = float(order_status['rate'])
        order_type = order_status['type']

        stop_price = None
        limit_price = None

        # TODO: is this comprehensive enough?
        #if order_type.endswith('limit'):
        #    limit_price = price
        #elif order_type.endswith('stop'):
        #    stop_price = price

        #executed_price = float(order_status['avg_execution_price'])
        executed_price = price

        # TODO: bitfinex does not specify comission. I could calculate it but not sure if it's worth it.
        commission = None

        #date = pd.Timestamp.utcfromtimestamp(float(order_status['timestamp']))
        #date = pytz.utc.localize(date)
        date = None

        order = Order(
            dt=date,
            asset=self.assets[order_status['symbol']],
            amount=amount,
            stop=stop_price,
            limit=limit_price,
            filled=filled,
            id=str(order_status['orderNumber']),
            commission=commission
        )
        order.status = status

        return order, executed_price
    

    def get_balances(self):
        log.debug('retrieving wallets balances')
        try:
            balances = self.api.returnbalances()
        except Exception as e:
            log.debug(e)
            raise ExchangeRequestError(error=e)

        if 'error' in balances:
            raise ExchangeRequestError(
                error='unable to fetch balance {}'.format(balances['error'])
            )

        std_balances = dict()
        for (key, value) in iteritems(balances):
            currency = key.lower()
            std_balances[currency] = float(value)

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

    def get_candles(self, data_frequency, assets, bar_count=None):
        """
        Retrieve OHLVC candles from Poloniex

        :param data_frequency:
        :param assets:
        :param bar_count:
        :return:

        Available Frequencies
        ---------------------
        '5m', '15m', '30m', '2h', '4h', '1D'
        """

        # TODO: use BcolzMinuteBarReader to read from cache
        if(data_frequency == '5m' or data_frequency == 'minute'): #TODO: Polo does not have '1m'
            frequency = 300
        elif(data_frequency == '15m'):
            frequency = 900
        elif(data_frequency == '30m'):
            frequency = 1800
        elif(data_frequency == '2h'):
            frequency = 7200
        elif(data_frequency == '4h'):
            frequency = 14400
        elif(data_frequency == '1D' or data_frequency == 'daily'):
            frequency = 86400
        else:
            raise InvalidHistoryFrequencyError(
                frequency=data_frequency
            )

        # Making sure that assets are iterable
        asset_list = [assets] if isinstance(assets, TradingPair) else assets
        ohlc_map = dict()

        for asset in asset_list:

            end = int(time.time())
            if(bar_count is None):
                start = end - 2 * frequency
            else:
                start = end - bar_count * frequency

            try: 
                response = self.api.returnchartdata(self.get_symbol(asset),frequency, start, end)
            except Exception as e:
                raise ExchangeRequestError(error=e)

            if 'error' in response:
                raise ExchangeRequestError(
                    error='Unable to retrieve candles: {}'.format(
                        response.content)
                )

            def ohlc_from_candle(candle):
                ohlc = dict(
                    open=np.float64(candle['open']),
                    high=np.float64(candle['high']),
                    low=np.float64(candle['low']),
                    close=np.float64(candle['close']),
                    volume=np.float64(candle['volume']),
                    price=np.float64(candle['close']),
                    last_traded=pd.Timestamp.utcfromtimestamp( candle['date'] )
                )

                return ohlc

            if bar_count is None:
                ohlc_map[asset] = ohlc_from_candle(response[0])
            else:
                ohlc_bars = []
                for candle in response:
                    ohlc = ohlc_from_candle(candle)
                    ohlc_bars.append(ohlc)
                ohlc_map[asset] = ohlc_bars

        return ohlc_map[assets] \
            if isinstance(assets, TradingPair) else ohlc_map


    def create_order(self, asset, amount, is_buy, style):
        pass
    '''
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
    '''

    def get_open_orders(self, asset='all'):
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
            if(asset=='all'):
                response = self.api.returnopenorders('all')
            else:
                response = self.api.returnopenorders(self.get_symbol(asset))
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if 'error' in response:
            raise ExchangeRequestError(
                error='Unable to retrieve open orders: {}'.format(
                    order_statuses['message'])
            )

        #TODO: Need to handle openOrders for 'all'
        orders = list()
        for order_status in response:
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
        pass
        '''
        try:
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
        '''

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
            response = self.api.cancelorder(order_id)
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if 'error' in response:
            raise OrderCancelError(
                order_id=order_id,
                exchange=self.name,
                error=response['error']
            )
        

    def tickers(self, assets):
        """
        Fetch ticket data for assets
        https://docs.bitfinex.com/v2/reference#rest-public-tickers

        :param assets:
        :return:
        """
        pass

        '''
        symbols = self._get_v2_symbols(assets)
        log.debug('fetching tickers {}'.format(symbols))

        try:
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

        tickers = response.json()

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
        '''

    def generate_symbols_json(self, filename=None):
        symbol_map = {}
        response = self.api.returnticker()
        for exchange_symbol in response:
            base, market = self.sanitize_curency_symbol(exchange_symbol).split('_')
            symbol = '{market}_{base}'.format( market=market, base=base )
            symbol_map[exchange_symbol] = dict(
                symbol = symbol,
                start_date = '2010-01-01'
            )

        if(filename is None):
            filename = get_exchange_symbols_filename(self.name)

        with open(filename,'w') as f:
            json.dump(symbol_map, f, sort_keys=True, indent=2, separators=(',',':'))
        
