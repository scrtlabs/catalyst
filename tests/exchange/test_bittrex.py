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
        pass

    def test_tickers(self):
        log.info('retrieving tickers')
        pass

    def get_account(self):
        log.info('retrieving account data')
        pass
