from catalyst.exchange.bitfinex.bitfinex import Bitfinex
from base import BaseExchangeTestCase
from logbook import Logger
from catalyst.finance.execution import (MarketOrder,
                                        LimitOrder,
                                        StopOrder,
                                        StopLimitOrder)
from catalyst.exchange.exchange_utils import get_exchange_auth

log = Logger('test_bitfinex')


class BitfinexTestCase(BaseExchangeTestCase):
    @classmethod
    def setup(self):
        log.info('creating bitfinex object')
        auth = get_exchange_auth('bitfinex')
        self.exchange = Bitfinex(
            key=auth['key'],
            secret=auth['secret'],
            base_currency='usd'
        )

    def test_order(self):
        log.info('creating order')
        asset = self.exchange.get_asset('eth_usd')
        order_id = self.exchange.order(
            asset=asset,
            style=LimitOrder(limit_price=200),
            limit_price=200,
            amount=0.5,
            stop_price=None
        )
        log.info('order created {}'.format(order_id))
        pass

    def test_open_orders(self):
        log.info('retrieving open orders')
        orders = self.exchange.get_open_orders()
        pass

    def test_get_order(self):
        log.info('retrieving order')
        pass

    def test_cancel_order(self):
        log.info('cancel order')
        pass

    def test_get_candles(self):
        log.info('retrieving candles')
        pass

    def test_tickers(self):
        log.info('retrieving tickers')
        tickers = self.exchange.tickers([
            self.exchange.get_asset('eth_usd'),
            self.exchange.get_asset('btc_usd')
        ])
        pass

    def test_get_account(self):
        log.info('retrieving account data')
        pass

    def test_get_balances(self):
        log.info('testing exchange balances')
        balances = self.exchange.get_balances()
        pass
