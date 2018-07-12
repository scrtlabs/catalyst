from logbook import Logger
from mock import patch, create_autospec, MagicMock, Mock
import pandas as pd

from ccxt.base.errors import RequestTimeout

from catalyst.exchange.exchange_errors import ExchangeRequestError
from .base import BaseExchangeTestCase
from catalyst.exchange.ccxt.ccxt_exchange import CCXT
from catalyst.exchange.exchange_execution import ExchangeLimitOrder
from catalyst.exchange.utils.exchange_utils import get_exchange_auth
from catalyst.finance.order import Order

log = Logger('test_ccxt')


class TestCCXT(BaseExchangeTestCase):
    @classmethod
    def setup(self):
        exchange_name = 'bittrex'
        auth = get_exchange_auth(exchange_name)
        self.exchange = CCXT(
            exchange_name=exchange_name,
            key=auth['key'],
            secret=auth['secret'],
            password='',
            quote_currency='usdt',
        )
        self.exchange.init()

    def create_orders_dict(self, asset, last_order):
        """
        create an orders dict which mocks the .orders object
        :param asset: TradingPair
        :param last_order: bool, adds another order to the dict.
                            mocks the functionality of the fetchOrder methods
        :return: dict(Order)
        """
        orders = dict()
        orders['208612980769'] = Order(
            dt=pd.to_datetime('2018-05-01 17:34', utc=True),
            asset=asset,
            amount=2,
            stop=None,
            limit=0.0025,
            id='208612980769'
        )
        orders['656797594'] = Order(
            dt=pd.to_datetime('2018-05-01 18:34', utc=True),
            asset=asset,
            amount=1,
            stop=None,
            limit=0.0027,
            id='656797594'
        )
        orders['656797494'] = Order(
            dt=pd.to_datetime('2018-05-01 18:54', utc=True),
            asset=asset,
            amount=7,
            stop=None,
            limit=0.00246,
            id='656797494'
        )
        if last_order:
            orders['111'] = Order(
                dt=pd.to_datetime('2018-05-01 19:54', utc=True),
                asset=asset,
                amount=2,
                stop=None,
                limit=0.00254,
                id='111'
            )
        return orders

    def create_trades_dict(self, symbol):
        """
        :param symbol: only for the side effect
        :return: list(dict)
        """
        trades = list()
        trades.append(
            {'info': {'globalTradeID': 369156767, 'tradeID': '8415970',
                      'rate': '0.0025', 'amount': '0.78', 'total': '0.0019',
                      'fee': '0.00250000', 'orderNumber': '208612980769',
                      'type': 'buy', 'category': 'exchange'},
             'datetime': pd.Timestamp.utcnow(),
             'symbol': 'ETH/USDT',
             'id': '8415970',
             'order': '208612980769',
             'type': 'limit',
             'side': 'buy',
             'price': 0.0025,
             'amount': 0.78,
             'cost': 0.0019,
             'fee': {'type': None, 'rate': 0.0025,
                     'cost': 0.0019690912999999997, 'currency': 'ETH'}
             }
        )

        trades.append(
            {'info': {'globalTradeID': 369156780, 'tradeID': '8415971',
                      'rate': '0.0025', 'amount': '1.22', 'total': '0.0031',
                      'fee': '0.0025', 'orderNumber': '208612980769',
                      'type': 'buy', 'category': 'exchange'},
             'datetime': pd.Timestamp.utcnow(),
             'symbol': 'ETH/USDT',
             'id': '8415971',
             'order': '208612980769',
             'type': 'limit',
             'side': 'buy',
             'price': 0.0025,
             'amount': 1.22,
             'cost': 0.0031,
             'fee': {'type': None, 'rate': 0.0025,
                     'cost': 0.0031, 'currency': 'ETH'}
             }
        )

        if self.last_trade:
            trades.append(
                {'info': {'globalTradeID': 369156784, 'tradeID': '8415972',
                          'rate': '0.0025', 'amount': '0.78',
                          'total': '0.0019', 'fee': '0.0025',
                          'orderNumber': '111', 'type': 'buy',
                          'category': 'exchange'},
                 'datetime': pd.Timestamp.utcnow(),
                 'symbol': 'ETH/USDT',
                 'id': '8415972',
                 'order': '111',
                 'type': 'limit',
                 'side': 'buy',
                 'price': 0.0025,
                 'amount': 2,
                 'cost': 0.005,
                 'fee': {'type': None, 'rate': 0.0025,
                         'cost': 0.005, 'currency': 'ETH'}
                 }
            )
        return trades

    def mod_last_order(self):
        """
        adds the last order into .orders
        :return:
        """
        self.last_order = True
        asset = [pair for pair in self.exchange.assets if
                 pair.symbol == 'eth_usdt'][0]
        orders_dict = self.create_orders_dict(asset, self.last_order)
        self.exchange.api.orders = orders_dict

    def compare_orders(self, observed, expected):
        """
        compares orders arguments to make sure that they are equal
        :param observed: Order
        :param expected: Order
        :return: bool
        """
        return observed.id == expected.id and \
            observed.amount == expected.amount and \
            observed.asset == expected.asset and \
            observed.limit == expected.limit

    def test_create_order_timeout_order(self):
        """
        create_order method
        tests the handling of a RequestTimeout exception and locating the
        order, if was created, using the fetchOrders method
        :return:
        """
        asset = [pair for pair in self.exchange.assets if
                 pair.symbol == 'eth_usdt'][0]
        amount = 2
        is_buy = True
        self.last_order = False
        price = 0.00254

        self.exchange.api = MagicMock(
            spec=[u'create_order', u'fetch_orders', u'orders', u'has',
                  u'amount_to_precision'])
        self.exchange.api.create_order.side_effect = RequestTimeout

        orders_dict = self.create_orders_dict(asset, self.last_order)
        self.exchange.api.orders = orders_dict
        self.exchange.api.has = {'fetchOrders': True}
        self.exchange.api.fetch_orders.side_effect = self.mod_last_order

        mock_style = create_autospec(ExchangeLimitOrder, return_value=price)
        mock_style.get_limit_price.return_value = price
        style = mock_style

        self.exchange.api.amount_to_precision = Mock(
            return_value=float(amount))

        with patch('catalyst.exchange.ccxt.ccxt_exchange.CCXT.get_symbol') as \
                mock_symbol:
            mock_symbol.return_value = 'ETH/USDT'
            observed_fetchOrders_order = self.exchange.create_order(
                asset, amount, is_buy, style)

        expected_fetchOrders_order = Order(
            dt=pd.to_datetime('2018-05-01 19:54', utc=True),
            asset=asset,
            amount=amount,
            stop=None,
            limit=price,
            id='111'
        )
        assert self.compare_orders(observed_fetchOrders_order,
                                   expected_fetchOrders_order) is True

    def test_create_order_timeout_open(self):
        """
        create_order method
        tests the handling of a RequestTimeout exception and locating the
        order, if was created, using the fetchOpenOrders method
        :return:
        """
        asset = [pair for pair in self.exchange.assets if
                 pair.symbol == 'eth_usdt'][0]
        amount = 2
        is_buy = True
        self.last_order = False
        price = 0.00254

        self.exchange.api = MagicMock(
            spec=[u'create_order', u'fetch_open_orders',
                  u'fetch_orders', u'orders', u'has', u'amount_to_precision'
                  ]
        )
        self.exchange.api.create_order.side_effect = RequestTimeout

        orders_dict = self.create_orders_dict(asset, self.last_order)
        self.exchange.api.orders = orders_dict
        self.exchange.api.has = {'fetchOpenOrders': True,
                                 'fetchOrders': 'emulated',
                                 'fetchClosedOrders': True
                                 }
        self.exchange.api.fetch_open_orders.side_effect = self.mod_last_order

        mock_style = create_autospec(ExchangeLimitOrder,
                                     return_value=price)
        mock_style.get_limit_price.return_value = price
        style = mock_style

        self.exchange.api.amount_to_precision = Mock(
            return_value=float(amount))

        with patch('catalyst.exchange.ccxt.ccxt_exchange.CCXT.get_symbol') as \
                mock_symbol:
            mock_symbol.return_value = 'ETH/USDT'
            observed_fetchOpen_order = self.exchange.create_order(
                asset, amount, is_buy, style)

        expected_fetchOpen_order = Order(
            dt=pd.to_datetime('2018-05-01 19:54', utc=True),
            asset=asset,
            amount=amount,
            stop=None,
            limit=price,
            id='111'
        )
        assert self.compare_orders(observed_fetchOpen_order,
                                   expected_fetchOpen_order) is True

    def test_create_order_timeout_closed(self):
        """
        create_order method
        tests the handling of a RequestTimeout exception and locating the
        order, if was created, using the fetchClosedOrders method
        :return:
        """
        asset = [pair for pair in self.exchange.assets if
                 pair.symbol == 'eth_usdt'][0]
        amount = 2
        is_buy = True
        self.last_order = False
        price = 0.00254

        self.exchange.api = MagicMock(
            spec=[u'create_order', u'fetch_closed_orders', u'orders', u'has',
                  u'amount_to_precision'])
        self.exchange.api.create_order.side_effect = RequestTimeout

        orders_dict = self.create_orders_dict(asset, self.last_order)
        self.exchange.api.orders = orders_dict
        self.exchange.api.has = {'fetchOpenOrders': False,
                                 'fetchClosedOrders': True
                                 }
        self.exchange.api.fetch_closed_orders.side_effect = self.mod_last_order

        mock_style = create_autospec(ExchangeLimitOrder,
                                     return_value=price)
        mock_style.get_limit_price.return_value = price
        style = mock_style

        self.exchange.api.amount_to_precision = Mock(
            return_value=float(amount))

        with patch('catalyst.exchange.ccxt.ccxt_exchange.CCXT.get_symbol') as \
                mock_symbol:
            mock_symbol.return_value = 'ETH/USDT'
            observed_fetchClosed_order = self.exchange.create_order(
                asset, amount, is_buy, style)

        expected_fetchClosed_order = Order(
            dt=pd.to_datetime('2018-05-01 19:54', utc=True),
            asset=asset,
            amount=amount,
            stop=None,
            limit=price,
            id='111'
        )
        assert self.compare_orders(observed_fetchClosed_order,
                                   expected_fetchClosed_order) is True

    def test_create_order_timeout_trade(self):
        """
        create_order method
        tests the handling of a RequestTimeout exception and locating the
        order, if was created, using the fetchTrades method.
        checks as well, the case that the order was not created at all,
        and makes sure an exception is raised in order to retry the
        creation of the order.
        :return:
        """
        asset = [pair for pair in self.exchange.assets if
                 pair.symbol == 'eth_usdt'][0]
        amount = 2
        is_buy = True
        self.last_order = False
        self.last_trade = False

        price = 0.00254
        stop_price = 0.00354

        self.exchange.api = MagicMock(
            spec=[u'create_order', u'fetch_my_trades', u'has',
                  u'fetch_open_orders', u'orders', u'fetch_closed_orders',
                  u'amount_to_precision']
        )
        self.exchange.api.create_order.side_effect = RequestTimeout

        orders_dict = self.create_orders_dict(asset, self.last_order)
        self.exchange.api.orders = orders_dict
        self.exchange.api.has = {'fetchClosedOrders': 'emulated',
                                 'fetchOrders': False,
                                 'fetchMyTrades': True,
                                 }
        self.exchange.api.fetch_my_trades.side_effect = self.create_trades_dict

        mock_style = create_autospec(ExchangeLimitOrder,
                                     return_value=price)
        mock_style.get_limit_price.return_value = price
        mock_style.get_stop_price.return_value = stop_price
        style = mock_style

        self.exchange.api.amount_to_precision = Mock(
            return_value=float(amount))

        # check the case there are no new trades and an exception is raised
        with patch('catalyst.exchange.ccxt.ccxt_exchange.CCXT.get_symbol') as \
                mock_symbol:
            mock_symbol.return_value = 'ETH/USDT'
            try:
                observed_fetchTrade_None = self.exchange.create_order(
                    asset, amount, is_buy, style)
                print(observed_fetchTrade_None)
            except ExchangeRequestError:
                pass

        # check the case there are trades which form a neew order
        self.last_trade = True
        with patch('catalyst.exchange.ccxt.ccxt_exchange.CCXT.get_symbol') as \
                mock_symbol:
            mock_symbol.return_value = 'ETH/USDT'
            observed_fetchTrade_order = self.exchange.create_order(
                asset, amount, is_buy, style)

        expected_fetchTrade_order = Order(
            dt=pd.Timestamp.utcnow(),
            asset=asset,
            amount=amount,
            stop=stop_price,
            limit=price,
            id='111'
        )
        assert self.compare_orders(observed_fetchTrade_order,
                                   expected_fetchTrade_order) is True

        # check the case there are no new trades or orders and an exception is
        # raised
        self.last_trade = False
        self.exchange.api.has['fetchOpenOrders'] = True
        with patch('catalyst.exchange.ccxt.ccxt_exchange.CCXT.get_symbol') as \
                mock_symbol:
            mock_symbol.return_value = 'ETH/USDT'
            try:
                observed_fetchTradeOrder_None = self.exchange.create_order(
                    asset, amount, is_buy, style)
                print(observed_fetchTradeOrder_None)
            except ExchangeRequestError:
                pass

    def test_process_order_timeout(self):
        """
        in case of a requestTimeout make sure that the process_order method
        returns an exception so the retry method can request the trades again.
        :return:
        """
        asset = [pair for pair in self.exchange.assets if
                 pair.symbol == 'eth_usdt'][0]
        amount = 2
        price = 0.0025
        order = Order(
            dt=pd.to_datetime('2018-05-01 19:54', utc=True),
            asset=asset,
            amount=amount,
            stop=None,
            limit=price,
            id='111'
        )
        self.exchange.api = MagicMock(
            spec=[u'create_order', u'fetch_my_trades', u'has',
                  u'fetch_open_orders', u'orders', u'fetch_closed_orders']
        )
        self.exchange.api.has = {'fetchClosedOrders': 'emulated',
                                 'fetchOrders': False,
                                 'fetchMyTrades': True,
                                 }
        with patch('catalyst.exchange.ccxt.ccxt_exchange.CCXT.get_trades') as \
                mock_trades:
            mock_trades.side_effect = RequestTimeout
            try:
                observed_transactions = self.exchange.process_order(order)
                print(observed_transactions)
            except ExchangeRequestError:
                pass

    # def test_order(self):
    #     log.info('creating order')
    #     asset = self.exchange.get_asset('eth_usdt')
    #     order_id = self.exchange.order(
    #         asset=asset,
    #         style=ExchangeLimitOrder(limit_price=1000),
    #         amount=1.01,
    #     )
    #     log.info('order created {}'.format(order_id))
    #     assert order_id is not None
    #     pass
    #
    # def test_open_orders(self):
    #     # log.info('retrieving open orders')
    #     # asset = self.exchange.get_asset('neo_eth')
    #     # orders = self.exchange.get_open_orders(asset)
    #     pass
    #
    # def test_get_order(self):
    #     log.info('retrieving order')
    #     order = self.exchange.get_order('2631386', 'neo_eth')
    #     # order = self.exchange.get_order('2631386')
    #     assert isinstance(order, Order)
    #     pass
    #
    # def test_cancel_order(self, ):
    #     log.info('cancel order')
    #     self.exchange.cancel_order('2631386', 'neo_eth')
    #     pass
    #
    # def test_get_candles(self):
    #     log.info('retrieving candles')
    #     candles = self.exchange.get_candles(
    #         freq='1T',
    #         assets=[self.exchange.get_asset('eth_btc')],
    #         bar_count=200,
    #         # start_dt=pd.to_datetime('2017-09-01', utc=True),
    #     )
    #
    #     for asset in candles:
    #         df = pd.DataFrame(candles[asset])
    #         df.set_index('last_traded', drop=True, inplace=True)
    #
    #     set_print_settings()
    #     print('got {} candles'.format(len(df)))
    #     print(df.head(10))
    #     print(df.tail(10))
    #     pass
    #
    # def test_tickers(self):
    #     log.info('retrieving tickers')
    #     assets = [
    #         self.exchange.get_asset('ada_eth'),
    #         self.exchange.get_asset('zrx_eth'),
    #     ]
    #     tickers = self.exchange.tickers(assets)
    #     assert len(tickers) == 2
    #     pass
    #
    # def test_my_trades(self):
    #     asset = self.exchange.get_asset('dsh_btc')
    #
    #     trades = self.exchange.get_trades(asset)
    #     assert trades
    #     pass
    #
    # def test_get_executed_order(self):
    #     log.info('retrieving executed order')
    #     asset = self.exchange.get_asset('eng_eth')
    #
    #     order = self.exchange.get_order('165784', asset)
    #     transactions = self.exchange.process_order(order)
    #     assert transactions
    #     pass
    #
    # def test_get_balances(self):
    #     log.info('testing wallet balances')
    #     # balances = self.exchange.get_balances()
    #     pass
    #
    # def test_get_account(self):
    #     log.info('testing account data')
    #     pass
    #
    # def test_orderbook(self):
    #     log.info('testing order book for bittrex')
    #     # asset = self.exchange.get_asset('eth_btc')
    #     # orderbook = self.exchange.get_orderbook(asset, 'all', limit=10)
    #     pass
    #
    # def test_get_fees(self):
    #     pass
