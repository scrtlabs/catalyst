import pytz
import six
import base64
import hashlib
import hmac
import json
import time
import requests
import pandas as pd
import collections
from catalyst.protocol import Portfolio, Account
# from websocket import create_connection
from catalyst.exchange.exchange import Exchange
from logbook import Logger
from catalyst.finance.order import ORDER_STATUS
from catalyst.exchange.exchange_order import ExchangeOrder
from catalyst.finance.execution import (MarketOrder,
                                        LimitOrder,
                                        StopOrder,
                                        StopLimitOrder)
from catalyst.data.data_portal import BASE_FIELDS
from catalyst.exchange.exchange_portfolio import ExchangePortfolio

BITFINEX_URL = 'https://api.bitfinex.com'
ASSETS = '{ "USDT_BTC": {"symbol":"btc_usd", "start_date": "2010-01-01"}, "ltcusd": {"symbol":"ltc_usd", "start_date": "2010-01-01"}, "ltcbtc": {"symbol":"ltc_btc", "start_date": "2010-01-01"}, "ethusd": {"symbol":"eth_usd", "start_date": "2010-01-01"}, "ethbtc": {"symbol":"eth_btc", "start_date": "2010-01-01"}, "etcbtc": {"symbol":"etc_btc", "start_date": "2010-01-01"}, "etcusd": {"symbol":"etc_usd", "start_date": "2010-01-01"}, "rrtusd": {"symbol":"rrt_usd", "start_date": "2010-01-01"}, "rrtbtc": {"symbol":"rrt_btc", "start_date": "2010-01-01"}, "zecusd": {"symbol":"zec_usd", "start_date": "2010-01-01"}, "zecbtc": {"symbol":"zec_btc", "start_date": "2010-01-01"}, "xmrusd": {"symbol":"xmr_usd", "start_date": "2010-01-01"}, "xmrbtc": {"symbol":"xmr_btc", "start_date": "2010-01-01"}, "dshusd": {"symbol":"dsh_usd", "start_date": "2010-01-01"}, "dshbtc": {"symbol":"dsh_btc", "start_date": "2010-01-01"}, "bccbtc": {"symbol":"bcc_btc", "start_date": "2010-01-01"}, "bcubtc": {"symbol":"bcu_btc", "start_date": "2010-01-01"}, "bccusd": {"symbol":"bcc_usd", "start_date": "2010-01-01"}, "bcuusd": {"symbol":"bcu_usd", "start_date": "2010-01-01"}, "xrpusd": {"symbol":"xrp_usd", "start_date": "2010-01-01"}, "xrpbtc": {"symbol":"xrp_btc", "start_date": "2010-01-01"}, "iotusd": {"symbol":"iot_usd", "start_date": "2010-01-01"}, "iotbtc": {"symbol":"iot_btc", "start_date": "2010-01-01"}, "ioteth": {"symbol":"iot_eth", "start_date": "2010-01-01"}, "eosusd": {"symbol":"eos_usd", "start_date": "2010-01-01"}, "eosbtc": {"symbol":"eos_btc", "start_date": "2010-01-01"}, "eoseth": {"symbol":"eos_eth", "start_date": "2010-01-01"} }'

log = Logger('Bitfinex')
warning_logger = Logger('AlgoWarning')


class Bitfinex(Exchange):
    def __init__(self, key, secret, base_currency, store):
        self.url = BITFINEX_URL
        self.key = key
        self.secret = secret
        self.id = 'b'
        self.name = 'bitfinex'
        self.assets = {}
        self.load_assets(ASSETS)
        self.base_currency = base_currency
        self.store = store

    def _request(self, operation, data, version='v1'):
        payload_object = {
            'request': '/{}/{}'.format(version, operation),
            'nonce': '{0:f}'.format(time.time() * 100000),  # convert to string
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
        is_buy = (amount > 0)

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

        if executed_price > 0 and price > 0:
            # TODO: This does not really work. Find a better way.
            commission = executed_price - price \
                if is_buy else price - executed_price
        else:
            commission = None

        date = pd.Timestamp.utcfromtimestamp(float(order_status['timestamp']))
        date = pytz.utc.localize(date)
        order = ExchangeOrder(
            dt=date,
            asset=self.assets[order_status['symbol']],
            amount=amount,
            stop=stop_price,
            limit=limit_price,
            filled=filled,
            id=order_status['id'],
            commission=commission
        )
        order.status = status
        order.executed_price = executed_price

        return order

    def update_portfolio(self):
        """
        Update the portfolio cash and position balances based on the
        latest ticker prices.

        :return:
        """
        response = self._request('balances', None)
        balances = response.json()
        if 'message' in balances:
            raise ValueError(
                'unable to fetch balance %s' % balances['message']
            )

        base_position = None
        for position in balances:
            if not base_position and position['type'] == 'exchange' \
                    and position['currency'] == self.base_currency:
                base_position = position

        if position is None:
            raise ValueError(
                'Base currency %s not found in portfolio' % self.base_currency
            )

        portfolio = self.store.portfolio
        portfolio.cash = float(base_position['available'])

        if portfolio.positions:
            assets = portfolio.positions.keys()
            tickers = self.tickers(assets)
            portfolio.positions_value = 0.0
            for ticker in tickers:
                # TODO: convert if the position is not in the base currency
                position = portfolio.positions[ticker['asset']]
                position.last_sale_price = ticker['last_price']
                position.last_sale_date = ticker['timestamp']

                portfolio.positions_value += \
                    position.amount * position.last_sale_price
                portfolio.portfolio_value = \
                    portfolio.positions_value + portfolio.cash

    @property
    def portfolio(self):
        """
        Return the Portfolio

        :return:
        """
        if self.store.portfolio is None:
            portfolio = ExchangePortfolio(
                store=self.store,
                start_date=pd.Timestamp.utcnow()
            )
            self.store.portfolio = portfolio
            self.update_portfolio()

            portfolio.starting_cash = portfolio.cash
        else:
            portfolio = self.store.portfolio

        return portfolio

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
    def positions(self):
        return self.portfolio.positions

    @property
    def time_skew(self):
        # TODO: research the time skew conditions
        return pd.Timedelta('0s')

    def subscribe_to_market_data(self, symbol):
        pass

    def get_spot_value(self, assets, field, dt=None, data_frequency='minute'):
        """
        Public API method that returns a scalar value representing the value
        of the desired asset's field at either the given dt.

        Parameters
        ----------
        assets : Asset, ContinuousFuture, or iterable of same.
            The asset or assets whose data is desired.
        field : {'open', 'high', 'low', 'close', 'volume',
                 'price', 'last_traded'}
            The desired field of the asset.
        dt : pd.Timestamp
            The timestamp for the desired value.
        data_frequency : str
            The frequency of the data to query; i.e. whether the data is
            'daily' or 'minute' bars

        Returns
        -------
        value : float, int, or pd.Timestamp
            The spot value of ``field`` for ``asset`` The return type is based
            on the ``field`` requested. If the field is one of 'open', 'high',
            'low', 'close', or 'price', the value will be a float. If the
            ``field`` is 'volume' the value will be a int. If the ``field`` is
            'last_traded' the value will be a Timestamp.

        Bitfinex timeframes
        -------------------
        Available values: '1m', '5m', '15m', '30m', '1h', '3h', '6h', '12h',
         '1D', '7D', '14D', '1M'
        """
        if field not in BASE_FIELDS:
            raise KeyError('Invalid column: ' + str(field))

        if isinstance(assets, collections.Iterable):
            values = list()
            for asset in assets:
                value = self.get_single_spot_value(
                    asset, field, data_frequency)
                values.append(value)

            return values
        else:
            return self.get_single_spot_value(
                assets, field, data_frequency)

    def get_single_spot_value(self, asset, field, data_frequency):
        symbol = self._get_v2_symbol(asset)
        log.debug(
            'fetching spot value {field} for symbol {symbol}'.format(
                symbol=symbol,
                field=field
            )
        )

        if data_frequency == 'minute':
            frequency = '1m'
        elif data_frequency == 'daily':
            frequency = '1D'
        else:
            raise NotImplementedError(
                'Unsupported frequency %s' % data_frequency
            )

        response = requests.get(
            '{url}/v2/candles/trade:{frequency}:{symbol}/last'.format(
                url=self.url,
                frequency=frequency,
                symbol=symbol
            )
        )
        candles = response.json()

        if 'message' in candles:
            raise ValueError(
                'Unable to retrieve candles: %s' % candles['message']
            )

        ohlc = dict(
            open=candles[1],
            high=candles[3],
            low=candles[4],
            close=candles[2],
            volume=candles[5],
            price=candles[2],
            last_traded=pd.Timestamp.utcfromtimestamp(candles[0] / 1000.0),
        )

        if field not in ohlc:
            raise KeyError('Invalid column: %s' % field)

        return ohlc[field]

    def order(self, asset, amount, limit_price, stop_price, style):
        """Place an order.

        Parameters
        ----------
        asset : Asset
            The asset that this order is for.
        amount : int
            The amount of shares to order. If ``amount`` is positive, this is
            the number of shares to buy or cover. If ``amount`` is negative,
            this is the number of shares to sell or short.
        limit_price : float, optional
            The limit price for the order.
        stop_price : float, optional
            The stop price for the order.
        style : ExecutionStyle, optional
            The execution style for the order.

        Returns
        -------
        order_id : str or None
            The unique identifier for this order, or None if no order was
            placed.

        Notes
        -----
        The ``limit_price`` and ``stop_price`` arguments provide shorthands for
        passing common execution styles. Passing ``limit_price=N`` is
        equivalent to ``style=LimitOrder(N)``. Similarly, passing
        ``stop_price=M`` is equivalent to ``style=StopOrder(M)``, and passing
        ``limit_price=N`` and ``stop_price=M`` is equivalent to
        ``style=StopLimitOrder(N, M)``. It is an error to pass both a ``style``
        and ``limit_price`` or ``stop_price``.

        Bitfinex Order Types
        --------------------
        LIMIT, MARKET, STOP, TRAILING STOP,
        EXCHANGE MARKET, EXCHANGE LIMIT, EXCHANGE STOP,
        EXCHANGE TRAILING STOP, FOK, EXCHANGE FOK.

        See Also
        --------
        :class:`catalyst.finance.execution.ExecutionStyle`
        :func:`catalyst.api.order_value`
        :func:`catalyst.api.order_percent`
        """
        if amount == 0:
            log.warn('skipping order amount of 0')
            return None

        base_currency = asset.symbol.split('_')[1]
        if base_currency.lower() != self.base_currency.lower():
            raise NotImplementedError(
                'Currency pairs must share their base with the exchange.'
            )

        is_buy = (amount > 0)

        if isinstance(style, MarketOrder):
            order_type = 'market'
        elif isinstance(style, LimitOrder):
            order_type = 'limit'
            price = limit_price
        elif isinstance(style, StopOrder):
            order_type = 'stop'
            price = stop_price
        elif isinstance(style, StopLimitOrder):
            log.warn('using limit order instead of stop/limit')
            # TODO: Not sure how to do this with the api. Investigate.
            order_type = 'limit'
            price = limit_price
        else:
            raise NotImplementedError('%s orders not available' % style)

        log.debug(
            'ordering {amount} {symbol} for {price}'.format(
                amount=amount,
                symbol=asset.symbol,
                price=price
            )
        )

        exchange_symbol = self.get_symbol(asset)
        req = dict(
            symbol=exchange_symbol,
            amount=str(float(abs(amount))),
            price=str(float(price)),
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

        response = self._request('order/new', req)
        exchange_order = response.json()
        if 'message' in exchange_order:
            raise ValueError(
                'unable to create Bitfinex order %s' % exchange_order[
                    'message']
            )

        order_id = exchange_order['id']
        order = ExchangeOrder(
            dt=pd.Timestamp.utcnow(),
            asset=asset,
            amount=amount,
            stop=style.get_stop_price(is_buy),
            limit=style.get_limit_price(is_buy),
            id=order_id
        )
        # TODO: is this required?
        order.broker_order_id = order_id

        self.portfolio.create_order(order)

        return order_id

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
        response = self._request('orders', None)
        order_statuses = response.json()
        if 'message' in order_statuses:
            raise ValueError(
                'Unable to retrieve open orders: %s' % order_statuses[
                    'message']
            )

        orders = list()
        for order_status in order_statuses:
            # TODO: filter by asset
            order = self._create_order(order_status)
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
        response = self._request('order/status', {'order_id': int(order_id)})
        order_status = response.json()

        if 'message' in order_status:
            raise ValueError(
                'Unable to retrieve order status: %s' % order_status['message']
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
            if isinstance(order_param, ExchangeOrder) else order_param

        response = self._request('order/cancel', {'order_id': order_id})
        status = response.json()
        if 'message' in status:
            raise ValueError(
                'Unable to cancel order: %s %s' % (order_id, status['message'])
            )

    def tickers(self, assets):
        """
        Fetch ticket data for assets
        https://docs.bitfinex.com/v2/reference#rest-public-tickers
        :param date:
        :param assets:
        :return:
        """
        symbols = self._get_v2_symbols(assets)
        log.debug('fetching tickers {}'.format(symbols))

        request = requests.get(
            '{url}/v2/tickers?symbols={symbols}'.format(
                url=self.url,
                symbols=','.join(symbols),
            )
        )
        tickers = request.json()

        if 'message' in tickers:
            raise ValueError(
                'Unable to retrieve tickers: %s' % tickers['message']
            )

        formatted_tickers = []
        for index, ticker in enumerate(tickers):
            if not len(ticker) == 11:
                raise ValueError('Invalid ticker: %s' % ticker)

            tick = dict(
                asset=assets[index],
                timestamp=pd.Timestamp.utcnow(),
                bid=ticker[1],
                ask=ticker[3],
                last_price=ticker[7],
                low=ticker[10],
                high=ticker[9],
                volume=ticker[8],
            )
            formatted_tickers.append(tick)

        log.debug('got tickers {}'.format(formatted_tickers))
        return formatted_tickers
