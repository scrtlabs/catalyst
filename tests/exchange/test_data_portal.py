import pandas as pd
from logbook import Logger

from catalyst import get_calendar
from catalyst.exchange.exchange_asset_finder import ExchangeAssetFinder
from catalyst.exchange.exchange_data_portal import (
    DataPortalExchangeBacktest,
    DataPortalExchangeLive
)
# from catalyst.exchange.utils.exchange_utils import get_common_assets
from catalyst.exchange.utils.factory import get_exchanges
# from test_utils import rnd_history_date_days, rnd_bar_count

log = Logger('test_bitfinex')


class TestExchangeDataPortal:
    @classmethod
    def setup(self):
        log.info('creating bitfinex exchange')
        exchanges = get_exchanges(['bitfinex', 'bittrex', 'poloniex'])
        open_calendar = get_calendar('OPEN')
        asset_finder = ExchangeAssetFinder()

        self.data_portal_live = DataPortalExchangeLive(
            exchanges=exchanges,
            asset_finder=asset_finder,
            trading_calendar=open_calendar,
            first_trading_day=pd.to_datetime('today', utc=True)
        )

        self.data_portal_backtest = DataPortalExchangeBacktest(
            exchanges=exchanges,
            asset_finder=asset_finder,
            trading_calendar=open_calendar,
            first_trading_day=None  # will set dynamically based on assets
        )

    def _test_get_history_window_live(self):
        # asset_finder = self.data_portal_live.asset_finder

        # assets = [
        #     asset_finder.lookup_symbol('eth_btc', self.bitfinex),
        #     asset_finder.lookup_symbol('eth_btc', self.bittrex)
        # ]
        # now = pd.Timestamp.utcnow()
        # data = self.data_portal_live.get_history_window(
        #     assets,
        #     now,
        #     10,
        #     '1m',
        #     'price')
        pass

    def _test_get_spot_value_live(self):
        # asset_finder = self.data_portal_live.asset_finder

        # assets = [
        #     asset_finder.lookup_symbol('eth_btc', self.bitfinex),
        #     asset_finder.lookup_symbol('eth_btc', self.bittrex)
        # ]
        # now = pd.Timestamp.utcnow()
        # value = self.data_portal_live.get_spot_value(
        #     assets, 'price', now, '1m')
        pass

    def _test_get_history_window_backtest(self):
        asset_finder = self.data_portal_live.asset_finder

        assets = [
            asset_finder.lookup_symbol('neo_btc', self.bitfinex),
        ]

        date = pd.to_datetime('2017-09-10', utc=True)
        data = self.data_portal_backtest.get_history_window(
            assets,
            date,
            10,
            '1m',
            'close',
            'minute')

        log.info('found history window: {}'.format(data))
        pass

    def _test_get_spot_value_backtest(self):
        asset_finder = self.data_portal_backtest.asset_finder

        assets = [
            asset_finder.lookup_symbol('neo_btc', self.bitfinex),
        ]

        date = pd.to_datetime('2017-09-10', utc=True)
        value = self.data_portal_backtest.get_spot_value(
            assets, 'close', date, 'minute')
        log.info('found spot value {}'.format(value))
        pass

    # def test_history_compare_exchanges(self):
    #     exchanges = get_exchanges(['bittrex', 'bitfinex', 'poloniex'])
    #     assets = get_common_assets(exchanges)
    #
    #     date = rnd_history_date_days()
    #     bar_count = rnd_bar_count()
    #     data = self.data_portal_backtest.get_history_window(
    #         assets=assets,
    #         end_dt=date,
    #         bar_count=bar_count,
    #         frequency='1d',
    #         field='close',
    #         data_frequency='daily'
    #     )
    #
    #     log.info('found history window: {}'.format(data))

    def _test_validate_resample(self):
        pass
