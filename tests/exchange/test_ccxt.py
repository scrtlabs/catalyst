import os
import tempfile

import pandas as pd
from catalyst.exchange.ccxt.ccxt_exchange import CCXT
from catalyst.finance.order import Order
from base import BaseExchangeTestCase
from logbook import Logger
from catalyst.exchange.exchange_utils import get_exchange_auth
from catalyst.utils.paths import ensure_directory

log = Logger('test_ccxt')


class TestCCXT(BaseExchangeTestCase):
    @classmethod
    def setup(self):
        exchange_name = 'poloniex'
        auth = get_exchange_auth(exchange_name)
        self.exchange = CCXT(
            exchange_name=exchange_name,
            key=auth['key'],
            secret=auth['secret'],
            base_currency=None,
            portfolio=None
        )

    def test_order(self):
        log.info('creating order')
        asset = self.exchange.get_asset('neo_btc')
        order_id = self.exchange.order(
            asset=asset,
            limit_price=0.0005,
            amount=1,
        )
        log.info('order created {}'.format(order_id))
        assert order_id is not None
        pass

    def test_open_orders(self):
        log.info('retrieving open orders')
        asset = self.exchange.get_asset('neo_btc')
        orders = self.exchange.get_open_orders(asset)
        pass

    def test_get_order(self):
        log.info('retrieving order')
        order = self.exchange.get_order(
            u'2c584020-9caf-4af5-bde0-332c0bba17e2')
        assert isinstance(order, Order)
        pass

    def test_cancel_order(self, ):
        log.info('cancel order')
        self.exchange.cancel_order(u'dc7bcca2-5219-4145-8848-8a593d2a72f9')
        pass

    def test_get_candles(self):
        log.info('retrieving candles')
        candles = self.exchange.get_candles(
            freq='5T',
            assets=[self.exchange.get_asset('eth_btc')],
            bar_count=200,
            start_dt=pd.to_datetime('2017-01-01', utc=True)
        )

        df = pd.DataFrame(candles)
        df.set_index('last_traded', drop=True, inplace=True)

        folder = os.path.join(
            tempfile.gettempdir(), 'catalyst', self.exchange.name, 'eth_btc'
        )
        ensure_directory(folder)

        path = os.path.join(folder, 'output.csv')
        df.to_csv(path)
        pass

    def test_tickers(self):
        log.info('retrieving tickers')
        tickers = self.exchange.tickers([
            self.exchange.get_asset('eth_btc'),
            self.exchange.get_asset('etc_btc')
        ])
        assert len(tickers) == 2
        pass

    def test_get_balances(self):
        log.info('testing wallet balances')
        balances = self.exchange.get_balances()
        pass

    def test_get_account(self):
        log.info('testing account data')
        pass

    def test_orderbook(self):
        log.info('testing order book for bittrex')
        asset = self.exchange.get_asset('eth_btc')
        orderbook = self.exchange.get_orderbook(asset)
        pass
