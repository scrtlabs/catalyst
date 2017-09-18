import pandas as pd
from catalyst import get_calendar
from logbook import Logger

from catalyst.exchange.asset_finder_exchange import AssetFinderExchange
from catalyst.exchange.bitfinex.bitfinex import Bitfinex
from catalyst.exchange.bittrex.bittrex import Bittrex
from catalyst.exchange.data_portal_exchange import DataPortalExchangeBacktest, \
    DataPortalExchangeLive
from catalyst.exchange.exchange_utils import get_exchange_auth

log = Logger('test_bitfinex')


class ExchangeDataPortalTestCase:
    @classmethod
    def setup(self):
        log.info('creating bitfinex exchange')
        auth_bitfinex = get_exchange_auth('bitfinex')
        bitfinex = Bitfinex(
            key=auth_bitfinex['key'],
            secret=auth_bitfinex['secret'],
            base_currency='usd'
        )

        log.info('creating bittrex exchange')
        auth_bitfinex = get_exchange_auth('bittrex')
        bittrex = Bittrex(
            key=auth_bitfinex['key'],
            secret=auth_bitfinex['secret'],
            base_currency='usd'
        )

        open_calendar = get_calendar('OPEN')
        asset_finder = AssetFinderExchange()
        self.data_portal_live = DataPortalExchangeLive(
            exchanges=dict(bitfinex=bitfinex, bittrex=bittrex),
            asset_finder=asset_finder,
            trading_calendar=open_calendar,
            first_trading_day=pd.to_datetime('today', utc=True)
        )

    def test_history_window_live(self):
        pass

    def test_spot_value_live(self):
        asset_finder = self.data_portal_live.asset_finder

        now = pd.Timestamp.utcnow()
        assets = [
            asset_finder.lookup_symbol('eth_usd',now,)
        ]
        value = self.data_portal_live.get_spot_value(
            assets, field, dt, data_frequency)
        pass
