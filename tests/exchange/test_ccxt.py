import pandas as pd
from logbook import Logger
from base import BaseExchangeTestCase

from catalyst.exchange.ccxt.ccxt_exchange import CCXT
from catalyst.finance.order import Order
from catalyst.exchange.exchange_utils import get_exchange_auth

log = Logger('test_ccxt')


class TestCCXT(BaseExchangeTestCase):
    @classmethod
    def setup(self):
        exchange_name = 'binance'
        auth = get_exchange_auth(exchange_name)
        self.exchange = CCXT(
            exchange_name=exchange_name,
            key=auth['key'],
            secret=auth['secret'],
            base_currency='eth',
        )
        self.exchange.init()

    def test_order(self):
        log.info('creating order')
        asset = self.exchange.get_asset('neo_eth')
        order_id = self.exchange.order(
            asset=asset,
            limit_price=0.07,
            amount=1,
        )
        log.info('order created {}'.format(order_id))
        assert order_id is not None
        pass

    def test_open_orders(self):
        # log.info('retrieving open orders')
        # asset = self.exchange.get_asset('neo_eth')
        # orders = self.exchange.get_open_orders(asset)
        pass

    def test_get_order(self):
        log.info('retrieving order')
        order = self.exchange.get_order('2631386', 'neo_eth')
        # order = self.exchange.get_order('2631386')
        assert isinstance(order, Order)
        pass

    def test_cancel_order(self, ):
        log.info('cancel order')
        self.exchange.cancel_order('2631386', 'neo_eth')
        pass

    def test_get_candles(self):
        log.info('retrieving candles')
        candles = self.exchange.get_candles(
            freq='5T',
            assets=[self.exchange.get_asset('eth_btc')],
            bar_count=200,
            start_dt=pd.to_datetime('2017-01-01', utc=True)
        )

        for asset in candles:
            df = pd.DataFrame(candles[asset])
            df.set_index('last_traded', drop=True, inplace=True)
        pass

    def test_tickers(self):
        log.info('retrieving tickers')
        assets = [
            self.exchange.get_asset('eng_eth'),
        ]
        tickers = self.exchange.tickers(assets)
        assert len(tickers) == 1
        pass

    def test_get_balances(self):
        log.info('testing wallet balances')
        # balances = self.exchange.get_balances()
        pass

    def test_get_account(self):
        log.info('testing account data')
        pass

    def test_orderbook(self):
        log.info('testing order book for bittrex')
        # asset = self.exchange.get_asset('eth_btc')
        # orderbook = self.exchange.get_orderbook(asset, 'all', limit=10)
        pass

    def test_get_fees(self):
        pass
