from catalyst.exchange.bittrex.bittrex import Bittrex
from catalyst.exchange.poloniex.poloniex import Poloniex
from catalyst.finance.order import Order
from base import BaseExchangeTestCase
from logbook import Logger
from catalyst.exchange.exchange_utils import get_exchange_auth

log = Logger('test_poloniex')


class TestPoloniex(BaseExchangeTestCase):
    @classmethod
    def setup(self):
        print ('creating poloniex object')
        auth = get_exchange_auth('poloniex')
        self.exchange = Poloniex(
            key=auth['key'],
            secret=auth['secret'],
            base_currency='btc'
        )

    def test_order(self):
        log.info('creating order')
        asset = self.exchange.get_asset('neos_btc')
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
        asset = self.exchange.get_asset('neos_btc')
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
        ohlcv_neo = self.exchange.get_candles(
            freq='5T',
            assets=self.exchange.get_asset('eth_btc')
        )
        ohlcv_neo_ubq = self.exchange.get_candles(
            freq='5T',
            assets=[
                self.exchange.get_asset('neos_btc'),
                self.exchange.get_asset('via_btc')
            ],
            bar_count=14
        )
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
        log.info('testing order book for poloniex')
        asset = self.exchange.get_asset('eth_btc')

        orderbook = self.exchange.get_orderbook(asset)
        pass
