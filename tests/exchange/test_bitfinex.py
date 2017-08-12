from catalyst.exchange.bitfinex import Bitfinex
from .base import BaseExchangeTestCase
from logbook import Logger
import pandas as pd
from catalyst.finance.execution import (MarketOrder,
                                        LimitOrder,
                                        StopOrder,
                                        StopLimitOrder)
from catalyst.assets._assets import Asset

log = Logger('BitfinexTestCase')


class BitfinexTestCase(BaseExchangeTestCase):
    def test_ticker(self):
        log.info('fetching ticker from bitfinex')
        bitfinex = Bitfinex()
        current_date = pd.Timestamp.utcnow()
        assets = [
            Asset(sid=0, exchange=bitfinex.name, symbol='eth_usd'),
            Asset(sid=1, exchange=bitfinex.name, symbol='etc_usd'),
            Asset(sid=2, exchange=bitfinex.name, symbol='eos_usd')
        ]
        tickers = bitfinex.tickers(date=current_date, assets=assets)
        log.info('got tickers {}'.format(tickers))

    def test_order(self):
        log.info('ordering from bitfinex')
        bitfinex = Bitfinex()
        asset = Asset(sid=0, exchange=bitfinex.name, symbol='eth_usd')
        order_id = bitfinex.order(
            asset=asset,
            style=LimitOrder(limit_price=200),
            limit_price=200,
            amount=1,
            stop_price=None
        )
        log.info('order created {}'.format(order_id))

    def test_cancel_order(self):
        log.info('canceling order from bitfinex')
        bitfinex = Bitfinex()
        response = bitfinex.cancel_order(order_id=2776936269)
        log.info('canceled order: {}'.format(response))

    def test_order_status(self):
        log.info('querying orders from bitfinex')
        bitfinex = Bitfinex()
        response = bitfinex.order_status(order_id=2776972180)
        log.info('the orders: {}'.format(response))

    def test_balance(self):
        log.info('querying positions from bitfinex')
        bitfinex = Bitfinex()
        balance = bitfinex.balance(currencies=['usd', 'etc', 'pez'])
        log.info('the balance: {}'.format(balance))
