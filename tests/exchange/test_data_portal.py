from datetime import timedelta

import os
import pandas as pd
from catalyst import get_calendar
from logbook import Logger

from catalyst.data.minute_bars import BcolzMinuteBarReader
from catalyst.exchange.asset_finder_exchange import AssetFinderExchange
from catalyst.exchange.bitfinex.bitfinex import Bitfinex
from catalyst.exchange.bittrex.bittrex import Bittrex
from catalyst.exchange.data_portal_exchange import DataPortalExchangeBacktest, \
    DataPortalExchangeLive
from catalyst.exchange.exchange_bundle import exchange_bundle
from catalyst.exchange.exchange_utils import get_exchange_auth
from catalyst.utils.run_algo import load_extensions

log = Logger('test_bitfinex')


class ExchangeDataPortalTestCase:
    @classmethod
    def setup(self):
        log.info('creating bitfinex exchange')
        auth_bitfinex = get_exchange_auth('bitfinex')
        self.bitfinex = Bitfinex(
            key=auth_bitfinex['key'],
            secret=auth_bitfinex['secret'],
            base_currency='usd'
        )

        log.info('creating bittrex exchange')
        auth_bitfinex = get_exchange_auth('bittrex')
        self.bittrex = Bittrex(
            key=auth_bitfinex['key'],
            secret=auth_bitfinex['secret'],
            base_currency='usd'
        )

        open_calendar = get_calendar('OPEN')
        asset_finder = AssetFinderExchange()

        self.data_portal_live = DataPortalExchangeLive(
            exchanges=dict(bitfinex=self.bitfinex, bittrex=self.bittrex),
            asset_finder=asset_finder,
            trading_calendar=open_calendar,
            first_trading_day=pd.to_datetime('today', utc=True)
        )
        self.data_portal_backtest = DataPortalExchangeBacktest(
            exchanges=dict(bitfinex=self.bitfinex),
            asset_finder=asset_finder,
            trading_calendar=open_calendar,
            first_trading_day=pd.to_datetime('today', utc=True)
        )

    def test_get_history_window_live(self):

        asset_finder = self.data_portal_live.asset_finder

        assets = [
            asset_finder.lookup_symbol('eth_btc', self.bitfinex),
            asset_finder.lookup_symbol('eth_btc', self.bittrex)
        ]
        now = pd.Timestamp.utcnow()
        data = self.data_portal_live.get_history_window(
            assets,
            now,
            10,
            '1m',
            'price')
        pass

    def test_get_spot_value_live(self):
        asset_finder = self.data_portal_live.asset_finder

        assets = [
            asset_finder.lookup_symbol('eth_btc', self.bitfinex),
            asset_finder.lookup_symbol('eth_btc', self.bittrex)
        ]
        now = pd.Timestamp.utcnow()
        value = self.data_portal_live.get_spot_value(
            assets, 'price', now, '1m')
        pass

    def test_get_spot_value_backtest(self):

        asset_finder = self.data_portal_backtest.asset_finder

        assets = [
            asset_finder.lookup_symbol('neo_btc', self.bitfinex),
        ]

        date = pd.Timestamp.utcnow() - timedelta(hours=8)
        value = self.data_portal_backtest.get_spot_value(
            assets, 'close', date, 'minute')
        pass

    def test_get_history_window_backtest(self):
        pass
