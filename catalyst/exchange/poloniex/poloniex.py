import json
import json
import time
from collections import defaultdict

import numpy as np
import pandas as pd
import pytz
from catalyst.assets._assets import TradingPair
from logbook import Logger
# import six
from six import iteritems

from catalyst.constants import LOG_LEVEL
# from websocket import create_connection
from catalyst.exchange.exchange import Exchange
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.exchange_errors import (
    ExchangeRequestError,
    InvalidHistoryFrequencyError,
    InvalidOrderStyle, OrphanOrderReverseError)
from catalyst.exchange.exchange_execution import ExchangeLimitOrder, \
    ExchangeStopLimitOrder
from catalyst.exchange.exchange_utils import get_exchange_symbols_filename, \
    download_exchange_symbols, get_symbols_string
from catalyst.exchange.poloniex.poloniex_api import Poloniex_api
from catalyst.finance.order import Order, ORDER_STATUS
from catalyst.finance.transaction import Transaction
from catalyst.protocol import Account

log = Logger('Poloniex', level=LOG_LEVEL)


class Poloniex(Exchange):
    def __init__(self, key, secret, base_currency, portfolio=None):
        self.api = Poloniex_api(key=key, secret=secret)
        self.name = 'poloniex'

        self.assets = dict()
        self.load_assets()

        self.local_assets = dict()
        self.load_assets(is_local=True)

        self.base_currency = base_currency
        self._portfolio = portfolio
        self.minute_writer = None
        self.minute_reader = None
        self.transactions = defaultdict(list)

        self.num_candles_limit = 2000
        self.max_requests_per_minute = 60
        self.request_cpt = dict()

        self.bundle = ExchangeBundle(self.name)

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
        # if order_status['is_cancelled']:
        #    status = ORDER_STATUS.CANCELLED
        # elif not order_status['is_live']:
        #    log.info('found executed order {}'.format(order_status))
        #    status = ORDER_STATUS.FILLED
        # else:
        status = ORDER_STATUS.OPEN

        amount = float(order_status['amount'])
        # filled = float(order_status['executed_amount'])
        filled = None

        if order_status['type'] == 'sell':
            amount = -amount
            # filled = -filled

        price = float(order_status['rate'])
        order_type = order_status['type']

        stop_price = None
        limit_price = None

        # TODO: is this comprehensive enough?
        # if order_type.endswith('limit'):
        #    limit_price = price
        # elif order_type.endswith('stop'):
        #    stop_price = price

        # executed_price = float(order_status['avg_execution_price'])
        executed_price = price

        # TODO: bitfinex does not specify comission. I could calculate it but not sure if it's worth it.
        commission = None

        # date = pd.Timestamp.utcfromtimestamp(float(order_status['timestamp']))
        # date = pytz.utc.localize(date)
        date = None

        order = Order(
            dt=date,
            asset=self.assets[order_status['symbol']],
            # No such field in Poloniex
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
        balances = self.api.returnbalances()
        try:
            log.debug('retrieving wallets balances')
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

    def get_candles(self, freq, assets, bar_count=None,
                    start_dt=None, end_dt=None):
        """
        Retrieve OHLVC candles from Poloniex

        :param freq:
        :param assets:
        :param bar_count:
        :return:

        Available Frequencies
        ---------------------
        '5m', '15m', '30m', '2h', '4h', '1D'
        """

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

        if freq == '1T' and (bar_count == 1 or bar_count is None):
            # TODO: use the order book instead
            # We use the 5m to fetch the last bar
            frequency = 300
        elif freq == '5T':
            frequency = 300
        elif freq == '15T':
            frequency = 900
        elif freq == '30T':
            frequency = 1800
        elif freq == '120T':
            frequency = 7200
        elif freq == '240T':
            frequency = 14400
        elif freq == '1D':
            frequency = 86400
        else:
            # Poloniex does not offer 1m data candles
            # It is likely to error out there frequently
            raise InvalidHistoryFrequencyError(frequency=freq)

        # Making sure that assets are iterable
        asset_list = [assets] if isinstance(assets, TradingPair) else assets
        ohlc_map = dict()

        for asset in asset_list:
            delta = end_dt - pd.to_datetime('1970-1-1', utc=True)
            end = int(delta.total_seconds())

            if bar_count is None:
                start = end - 2 * frequency
            else:
                start = end - bar_count * frequency

            try:
                response = self.api.returnchartdata(
                    self.get_symbol(asset), frequency, start, end
                )
            except Exception as e:
                raise ExchangeRequestError(error=e)

            if 'error' in response:
                raise ExchangeRequestError(
                    error='Unable to retrieve candles: {}'.format(
                        response.content)
                )

            def ohlc_from_candle(candle):
                last_traded = pd.Timestamp.utcfromtimestamp(candle['date'])
                last_traded = last_traded.replace(tzinfo=pytz.UTC)

                ohlc = dict(
                    open=np.float64(candle['open']),
                    high=np.float64(candle['high']),
                    low=np.float64(candle['low']),
                    close=np.float64(candle['close']),
                    volume=np.float64(candle['volume']),
                    price=np.float64(candle['close']),
                    last_traded=last_traded
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
        """
        Creating order on the exchange.

        :param asset:
        :param amount:
        :param is_buy:
        :param style:
        :return:
        """
        exchange_symbol = self.get_symbol(asset)

        if isinstance(style, ExchangeLimitOrder) or isinstance(style,
                                                               ExchangeStopLimitOrder):
            if isinstance(style, ExchangeStopLimitOrder):
                log.warn('{} will ignore the stop price'.format(self.name))

            price = style.get_limit_price(is_buy)

            try:
                if (is_buy):
                    response = self.api.buy(exchange_symbol, amount, price)
                else:
                    response = self.api.sell(exchange_symbol, -amount, price)
            except Exception as e:
                raise ExchangeRequestError(error=e)

            date = pd.Timestamp.utcnow()

            if ('orderNumber' in response):
                order_id = str(response['orderNumber'])
                order = Order(
                    dt=date,
                    asset=asset,
                    amount=amount,
                    stop=style.get_stop_price(is_buy),
                    limit=style.get_limit_price(is_buy),
                    id=order_id
                )
                return order
            else:
                log.warn(
                    '{} order failed: {}'.format('buy' if is_buy else 'sell',
                                                 response['error']))
                return None
        else:
            raise InvalidOrderStyle(exchange=self.name,
                                    style=style.__class__.__name__)

    def get_open_orders(self, asset='all'):
        """Retrieve all of the current open orders.

        Parameters
        ----------
        asset : Asset
            If passed and not 'all', return only the open orders for the given
            asset instead of all open orders.

        Returns
        -------
        open_orders : dict[list[Order]] or list[Order]
            If 'all' is passed this will return a dict mapping Assets
            to a list containing all the open orders for the asset.
            If an asset is passed then this will return a list of the open
            orders for this asset.
        """

        return self.portfolio.open_orders

        """
            TODO: Why going to the exchange if we already have this info locally?
                  And why creating all these Orders if we later discard them?
        """

        try:
            if (asset == 'all'):
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

        print(self.portfolio.open_orders)

        # TODO: Need to handle openOrders for 'all'
        orders = list()
        for order_status in response:
            order, executed_price = self._create_order(
                order_status)  # will Throw error b/c Polo doesn't track order['symbol']
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
            order = self._portfolio.open_orders[order_id]
        except Exception as e:
            raise OrphanOrderError(order_id=order_id, exchange=self.name)

        return order

        # TODO: Need to decide whether we fetch orders locally or from exchnage
        # The code below is ignored

        try:
            response = self.api.returnopenorders(self.get_symbol(order.sid))
        except Exception as e:
            raise ExchangeRequestError(error=e)

        for o in response:
            if (int(o['orderNumber']) == int(order_id)):
                return order

        return None

    def cancel_order(self, order_param):
        """Cancel an open order.

        Parameters
        ----------
        order_param : str or Order
            The order_id or order object to cancel.
        """

        if (isinstance(order_param, Order)):
            order = order_param
        else:
            order = self._portfolio.open_orders[order_param]

        try:
            response = self.api.cancelorder(order.id)
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if 'error' in response:
            log.info(
                'Unable to cancel order {order_id} on exchange {exchange} {error}.'.format(
                    order_id=order.id,
                    exchange=self.name,
                    error=response['error']
                ))

            # raise OrderCancelError(
            #    order_id=order.id,
            #    exchange=self.name,
            #    error=response['error']
            # )

        self.portfolio.remove_order(order)

    def tickers(self, assets):
        """
        Fetch ticket data for assets
        https://docs.bitfinex.com/v2/reference#rest-public-tickers

        :param assets:
        :return:
        """
        symbols = self.get_symbols(assets)

        log.debug('fetching tickers {}'.format(symbols))

        try:
            response = self.api.returnticker()
        except Exception as e:
            raise ExchangeRequestError(error=e)

        if 'error' in response:
            raise ExchangeRequestError(
                error='Unable to retrieve tickers: {}'.format(
                    response['error'])
            )

        ticks = dict()

        for index, symbol in enumerate(symbols):
            ticks[assets[index]] = dict(
                timestamp=pd.Timestamp.utcnow(),
                bid=float(response[symbol]['highestBid']),
                ask=float(response[symbol]['lowestAsk']),
                last_price=float(response[symbol]['last']),
                low=float(response[symbol]['lowestAsk']),
                # TODO: Polo does not provide low
                high=float(response[symbol]['highestBid']),
                # TODO: Polo does not provide high
                volume=float(response[symbol]['baseVolume']),
            )

        log.debug('got tickers {}'.format(ticks))
        return ticks

    def generate_symbols_json(self, filename=None, source_dates=False):
        symbol_map = {}

        if not source_dates:
            fn, r = download_exchange_symbols(self.name)
            with open(fn) as data_file:
                cached_symbols = json.load(data_file)

        response = self.api.returnticker()

        for exchange_symbol in response:
            base, market = self.sanitize_curency_symbol(exchange_symbol).split(
                '_')
            symbol = '{market}_{base}'.format(market=market, base=base)

            if (source_dates):
                start_date = self.get_symbol_start_date(exchange_symbol)
            else:
                try:
                    start_date = cached_symbols[exchange_symbol]['start_date']
                except KeyError as e:
                    start_date = time.strftime('%Y-%m-%d')

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
        try:
            r = self.api.returnchartdata(symbol, 86400, pd.to_datetime(
                '2010-1-1').value // 10 ** 9)
        except Exception as e:
            raise ExchangeRequestError(error=e)

        return time.strftime('%Y-%m-%d', time.gmtime(int(r[0]['date'])))

    def check_open_orders(self):
        """
        Need to override this function for Poloniex:

        Loop through the list of open orders in the Portfolio object.
        Check if any transactions have been executed:
            If so, create a transaction and apply to the Portfolio.
        Check if the order is still open:
            If not, remove it from open orders

        :return:
        transactions: Transaction[]
        """
        transactions = list()
        if self.portfolio.open_orders:
            for order_id in list(self.portfolio.open_orders):

                order = self._portfolio.open_orders[order_id]
                log.debug('found open order: {}'.format(order_id))

                try:
                    order_open = self.get_order(order_id)
                except Exception as e:
                    raise ExchangeRequestError(error=e)

                if (order_open):
                    delta = pd.Timestamp.utcnow() - order.dt
                    log.info(
                        'order {order_id} still open after {delta}'.format(
                            order_id=order_id,
                            delta=delta)
                    )

                try:
                    response = self.api.returnordertrades(order_id)
                except Exception as e:
                    raise ExchangeRequestError(error=e)

                if ('error' in response):
                    if (not order_open):
                        raise OrphanOrderReverseError(order_id=order_id,
                                                      exchange=self.name)
                else:
                    for tx in response:
                        """
                            We maintain a list of dictionaries of transactions that correspond to
                            partially filled orders, indexed by order_id. Every time we query 
                            executed transactions from the exchange, we check if we had that 
                            transaction for that order already. If not, we process it.

                            When an order if fully filled, we flush the dict of transactions  
                            associated with that order.
                        """
                        if (not filter(
                                lambda item: item['order_id'] == tx['tradeID'],
                                self.transactions[order_id])):
                            log.debug(
                                'Got new transaction for order {}: amount {}, price {}'.format(
                                    order_id, tx['amount'], tx['rate']))
                            tx['amount'] = float(tx['amount'])
                            if (tx['type'] == 'sell'):
                                tx['amount'] = -tx['amount']
                            transaction = Transaction(
                                asset=order.asset,
                                amount=tx['amount'],
                                dt=pd.to_datetime(tx['date'], utc=True),
                                price=float(tx['rate']),
                                order_id=tx['tradeID'],
                                # it's a misnomer, but keeping it for compatibility
                                commission=float(tx['fee'])
                            )
                            self.transactions[order_id].append(transaction)
                            self.portfolio.execute_transaction(transaction)
                            transactions.append(transaction)

                    if (not order_open):
                        """
                            Since transactions have been executed individually
                            the only thing left to do is remove them from list of open_orders
                        """
                        del self.portfolio.open_orders[order_id]
                        del self.transactions[order_id]

        return transactions

    def get_orderbook(self, asset, order_type='all'):
        exchange_symbol = asset.exchange_symbol
        data = self.api.returnOrderBook(market=exchange_symbol)

        result = dict()
        for order_type in data:
            # TODO: filter by type
            if order_type != 'asks' and order_type != 'bids':
                continue

            result[order_type] = []
            for entry in data[order_type]:
                if len(entry) == 2:
                    result[order_type].append(
                        dict(
                            rate=float(entry[0]),
                            quantity=float(entry[1])
                        )
                    )
        return result
