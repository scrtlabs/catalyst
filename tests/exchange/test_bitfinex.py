from catalyst.exchange.bitfinex import Bitfinex
from .base import BaseExchangeTestCase
from logbook import Logger
import pandas as pd
from catalyst.finance.execution import (MarketOrder,
                                        LimitOrder,
                                        StopOrder,
                                        StopLimitOrder)

log = Logger('BitfinexTestCase')


class BitfinexTestCase(BaseExchangeTestCase):
    def test_positions(self):
        log.info('querying positions from bitfinex')
        bitfinex = Bitfinex()
        balance = bitfinex.positions()
        log.info('the balance: {}'.format(balance))
        pass

    def test_portfolio(self):
        log.info('fetching portfolio data')
        pass

    def test_account(self):
        log.info('fetching account data')
        pass

    def test_time_skew(self):
        log.info('time skew not implemented')
        pass

    def test_get_open_orders(self):
        log.info('fetching open orders')
        bitfinex = Bitfinex()
        order_id = bitfinex.get_open_orders()
        log.info('open orders: {}'.format(order_id))
        pass

    def test_order(self):
        log.info('ordering from bitfinex')
        bitfinex = Bitfinex()
        order_id = bitfinex.order(
            asset=bitfinex.get_asset('eth_usd'),
            style=LimitOrder(limit_price=200),
            limit_price=200,
            amount=1,
            stop_price=None
        )
        log.info('order created {}'.format(order_id))
        pass

    def test_get_order(self):
        log.info('querying orders from bitfinex')
        bitfinex = Bitfinex()
        response = bitfinex.get_order(order_id=3330866978)
        log.info('the order: {}'.format(response))
        pass

    def test_cancel_order(self):
        log.info('canceling order from bitfinex')
        bitfinex = Bitfinex()
        response = bitfinex.cancel_order(order_id=3330847408)
        log.info('canceled order: {}'.format(response))
        pass

    def test_get_spot_value(self):
        log.info('spot value not implemented')
        bitfinex = Bitfinex()
        assets = [
            bitfinex.get_asset('eth_usd'),
            bitfinex.get_asset('etc_usd'),
            bitfinex.get_asset('eos_usd'),
        ]
        # assets = bitfinex.get_asset('eth_usd')
        value = bitfinex.get_spot_value(
            assets=assets,
            field='close',
            data_frequency='minute'
        )
        pass

    def test_tickers(self):
        log.info('fetching ticker from bitfinex')
        bitfinex = Bitfinex()
        current_date = pd.Timestamp.utcnow()
        assets = [
            bitfinex.get_asset('eth_usd'),
            bitfinex.get_asset('etc_usd'),
            bitfinex.get_asset('eos_usd'),
        ]
        tickers = bitfinex.tickers(date=current_date, assets=assets)
        log.info('got tickers {}'.format(tickers))
        pass
