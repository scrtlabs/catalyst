import random

from logbook import Logger
from pandas.util.testing import assert_frame_equal

import pandas as pd

from catalyst import get_calendar
from catalyst.exchange.asset_finder_exchange import AssetFinderExchange
from catalyst.exchange.exchange_data_portal import DataPortalExchangeBacktest
from catalyst.exchange.test_utils import select_random_exchanges, output_df, \
    select_random_assets

log = Logger('TestSuiteExchange')


class TestSuiteBundle:
    @staticmethod
    def get_data_portal(exchange_names):
        open_calendar = get_calendar('OPEN')
        asset_finder = AssetFinderExchange()

        data_portal = DataPortalExchangeBacktest(
            exchange_names=exchange_names,
            asset_finder=asset_finder,
            trading_calendar=open_calendar,
            first_trading_day=None  # will set dynamically based on assets
        )
        return data_portal

    def compare_bundle_with_exchange(self, exchange, assets, end_dt, bar_count,
                                     freq, data_portal):
        """
        Creates DataFrames from the bundle and exchange for the specified
        data set.

        Parameters
        ----------
        exchange: Exchange
        assets
        end_dt
        bar_count
        sample_minutes

        Returns
        -------

        """
        log.info('creating data sample from bundle')
        df1 = data_portal.get_history_window(
            assets=assets,
            end_dt=end_dt,
            bar_count=bar_count,
            frequency=freq,
            field='close',
            data_frequency='minute'
        )
        path = output_df(df1, assets, '{}_resampled'.format(freq))
        log.info('saved resampled bundle candles: {}\n{}'.format(
            path, df1.tail(10))
        )

        log.info('creating data sample from exchange api')
        candles = exchange.get_candles(
            end_dt=end_dt,
            freq=freq,
            assets=assets,
            bar_count=bar_count
        )

        series = dict()
        for asset in assets:
            series[asset] = pd.Series(
                data=[candle['close'] for candle in candles[asset]],
                index=[candle['last_traded'] for candle in candles[asset]]
            )

        df2 = pd.DataFrame(series)
        path = output_df(df2, assets, '{}_api'.format(freq))
        log.info('saved exchange api candles: {}\n{}'.format(
            path, df2.tail(10))
        )

        try:
            assert_frame_equal(df1, df2)
            return True
        except:
            log.warn('differences found in dataframes')
            return False

    def test_validate_bundles(self):
        exchange_population = 3
        asset_population = 3
        data_frequency = random.choice(['minute', 'daily'])

        bundle = 'dailyBundle' if data_frequency == 'daily' else 'minuteBundle'
        exchanges = select_random_exchanges(
            population=exchange_population,
            features=[bundle],
        )  # Type: list[Exchange]

        data_portal = TestSuiteBundle.get_data_portal(
            [exchange.name for exchange in exchanges]
        )
        for exchange in exchanges:
            exchange.init()

            frequencies = exchange.get_candle_frequencies(data_frequency)
            freq = random.sample(frequencies, 1)[0]

            bar_count = random.randint(1, 10)
            end_dt = pd.Timestamp.utcnow().floor('1T')
            dt_range = pd.date_range(
                end=end_dt, periods=bar_count, freq=freq
            )
            assets = select_random_assets(
                exchange.assets, asset_population
            )
            self.compare_bundle_with_exchange(
                exchange=exchange,
                assets=assets,
                end_dt=dt_range[-1],
                bar_count=bar_count,
                freq=freq,
                data_portal=data_portal,
            )
