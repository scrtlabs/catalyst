import six
import base64
import hashlib
import hmac
import json
import time
import requests
import pandas as pd
from catalyst.protocol import Portfolio, Account
# from websocket import create_connection
from catalyst.exchange.exchange import Exchange, RTVolumeBar, Position
from logbook import Logger
from catalyst.finance.order import Order, ORDER_STATUS
from catalyst.finance.execution import (MarketOrder,
                                        LimitOrder,
                                        StopOrder,
                                        StopLimitOrder)

BITFINEX_URL = 'https://api.bitfinex.com'
BITFINEX_KEY = 'hjZ7DZzwbBZsIZPWeSSQtrWCPNwyhxw96r3LnY7jtOH'
BITFINEX_SECRET = b'LilCoxcqUnHKBcGtrttwCIv4qONTdjuFMSdz8Rxh6OM'
ASSETS = '{ "btcusd": {"symbol":"btc_usd", "start_date": "2010-01-01"}, "ltcusd": {"symbol":"ltc_usd", "start_date": "2010-01-01"}, "ltcbtc": {"symbol":"ltc_btc", "start_date": "2010-01-01"}, "ethusd": {"symbol":"eth_usd", "start_date": "2010-01-01"}, "ethbtc": {"symbol":"eth_btc", "start_date": "2010-01-01"}, "etcbtc": {"symbol":"etc_btc", "start_date": "2010-01-01"}, "etcusd": {"symbol":"etc_usd", "start_date": "2010-01-01"}, "rrtusd": {"symbol":"rrt_usd", "start_date": "2010-01-01"}, "rrtbtc": {"symbol":"rrt_btc", "start_date": "2010-01-01"}, "zecusd": {"symbol":"zec_usd", "start_date": "2010-01-01"}, "zecbtc": {"symbol":"zec_btc", "start_date": "2010-01-01"}, "xmrusd": {"symbol":"xmr_usd", "start_date": "2010-01-01"}, "xmrbtc": {"symbol":"xmr_btc", "start_date": "2010-01-01"}, "dshusd": {"symbol":"dsh_usd", "start_date": "2010-01-01"}, "dshbtc": {"symbol":"dsh_btc", "start_date": "2010-01-01"}, "bccbtc": {"symbol":"bcc_btc", "start_date": "2010-01-01"}, "bcubtc": {"symbol":"bcu_btc", "start_date": "2010-01-01"}, "bccusd": {"symbol":"bcc_usd", "start_date": "2010-01-01"}, "bcuusd": {"symbol":"bcu_usd", "start_date": "2010-01-01"}, "xrpusd": {"symbol":"xrp_usd", "start_date": "2010-01-01"}, "xrpbtc": {"symbol":"xrp_btc", "start_date": "2010-01-01"}, "iotusd": {"symbol":"iot_usd", "start_date": "2010-01-01"}, "iotbtc": {"symbol":"iot_btc", "start_date": "2010-01-01"}, "ioteth": {"symbol":"iot_eth", "start_date": "2010-01-01"}, "eosusd": {"symbol":"eos_usd", "start_date": "2010-01-01"}, "eosbtc": {"symbol":"eos_btc", "start_date": "2010-01-01"}, "eoseth": {"symbol":"eos_eth", "start_date": "2010-01-01"} }'

log = Logger('Bitfinex')
warning_logger = Logger('AlgoWarning')


class Bitfinex(Exchange):
    def __init__(self):
        self.url = BITFINEX_URL
        self.key = BITFINEX_KEY
        self.secret = BITFINEX_SECRET
        self.id = 'b'
        self.name = 'bitfinex'
        self.orders = {}
        self.assets = {}
        self.load_assets(ASSETS)

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

    def _get_v2_symbols(self, assets):
        """
        Workaround to support Bitfinex v2
        TODO: Might require a separate asset dictionary

        :param assets:
        :return:
        """

        v2_symbols = []
        for asset in assets:
            pair = asset.symbol.split('_')
            symbol = 't' + pair[0].upper() + pair[1].upper()
            v2_symbols.append(symbol)
        return v2_symbols

    @property
    def portfolio(self):
        """
        TODO: I'm not sure how that's used yet
        :return: 
        """
        portfolio = Portfolio()
        portfolio.capital_used = None
        portfolio.starting_cash = None

        portfolio.portfolio_value = None
        portfolio.pnl = None
        portfolio.cash = None

        portfolio.returns = None
        portfolio.start_date = None
        portfolio.positions = self.positions
        portfolio.positions_value = None
        portfolio.positions_exposure = None

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
        response = self._request('balances', None)
        positions = response.json()
        if 'message' in positions:
            raise ValueError(
                'unable to fetch balance %s' % positions['message']
            )

        return positions

    @property
    def time_skew(self):
        # TODO: research the time skew conditions
        return None

    def subscribe_to_market_data(self, symbol):
        pass

    def get_spot_value(self, assets, field, dt, data_frequency):
        raise NotImplementedError()

    # TODO: why repeating prices if already in style?
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
            raise NotImplementedError('Stop/limit orders not available')

        exchange_symbol = self.get_symbol(asset)
        req = dict(
            symbol=exchange_symbol,
            amount=str(float(amount)),
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

        order = Order(
            dt=pd.Timestamp.utcnow(),
            asset=asset,
            amount=amount,
            stop=style.get_stop_price(is_buy),
            limit=style.get_limit_price(is_buy),
        )

        order_id = order.broker_order_id = exchange_order['id']
        self.orders[order_id] = order

        return order_id

    def get_open_orders(self, asset):
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
        # TODO: map to asset
        response = self._request('orders', None)
        orders = response.json()
        # TODO: what is the right format?
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

        result = dict(exchange=self.name)

        if order_status['is_cancelled']:
            warning_logger.warn(
                'removing cancelled order from the open orders list %s',
                order_status)
            result['status'] = 'canceled'

        elif not order_status['is_live']:
            log.info('found executed order %s', order_status)
            result['status'] = 'closed'
            result['executed_price'] = \
                float(order_status['avg_execution_price'])
            result['executed_amount'] = \
                float(order_status['executed_amount'])

        else:
            result['status'] = 'open'

        # TODO: what's the right format?
        return result

    def cancel_order(self, order_id):
        """Cancel an open order.

        Parameters
        ----------
        order_param : str or Order
            The order_id or order object to cancel.
        """
        response = self._request('order/cancel', {'order_id': order_id})
        status = response.json()
        return status

    def tickers(self, date, assets):
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
                timestamp=date,
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
