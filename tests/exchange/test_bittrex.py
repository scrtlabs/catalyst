from catalyst.exchange.bittrex.bittrex import Bittrex
from .base import BaseExchangeTestCase
from logbook import Logger
import pandas as pd
from catalyst.finance.execution import (MarketOrder,
                                        LimitOrder,
                                        StopOrder,
                                        StopLimitOrder)
from catalyst.exchange.exchange_utils import get_exchange_auth

log = Logger('test_bittrex')


class BittrexTestCase(BaseExchangeTestCase):
    @classmethod
    def setup(self):
        print ('creating bittrex object')
        auth = get_exchange_auth('bittrex')
        self.exchange = Bittrex(
            key=auth['key'],
            secret=auth['secret'],
            base_currency='usd'
        )

    def test_order(self):
        log.info('creating order')
        asset = self.exchange.get_asset('neo_eth')
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
        pass

    def test_get_order(self):
        log.info('retrieving order')
        pass

    def test_cancel_order(self):
        log.info('cancel order')
        pass

    def test_get_candles(self):
        log.info('retrieving candles')
        ohlcv_neo = self.exchange.get_candles(
            data_frequency='5m',
            assets=self.exchange.get_asset('neo_btc')
        )
        ohlcv_neo_ubq = self.exchange.get_candles(
            data_frequency='5m',
            assets=[
                self.exchange.get_asset('neo_btc'),
                self.exchange.get_asset('ubq_btc')
            ],
            bar_count=14
        )
        pass

    def test_tickers(self):
        log.info('retrieving tickers')
        pass

    def get_account(self):
        log.info('retrieving account data')
        pass
