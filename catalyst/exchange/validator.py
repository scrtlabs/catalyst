import os
import tempfile

import pandas as pd
import six
from catalyst.assets._assets import TradingPair, get_calendar
from logbook import Logger
from pandas.util.testing import assert_frame_equal

from catalyst.constants import LOG_LEVEL
from catalyst.exchange.asset_finder_exchange import AssetFinderExchange
from catalyst.exchange.exchange_data_portal import DataPortalExchangeBacktest
from catalyst.exchange.factory import get_exchanges
from catalyst.utils.paths import ensure_directory

log = Logger('Validator', level=LOG_LEVEL)


def output_df(df, assets, name=None):
    """
    Outputs a price DataFrame to a temp folder.

    Parameters
    ----------
    df: pd.DataFrame
    assets
    name

    Returns
    -------

    """
    if isinstance(assets, TradingPair):
        exchange_folder = assets.exchange
        asset_folder = assets.symbol
    else:
        exchange_folder = ','.join([asset.exchange for asset in assets])
        asset_folder = ','.join([asset.symbol for asset in assets])

    folder = os.path.join(
        tempfile.gettempdir(), 'catalyst', exchange_folder, asset_folder
    )
    ensure_directory(folder)

    if name is None:
        name = 'output'

    path = os.path.join(folder, '{}.csv'.format(name))
    df.to_csv(path)

    return path


class Validator(object):
    def __init__(self, data_portal):
        self.data_portal = data_portal

    def compare_bundle_with_exchange(self, exchange, assets, end_dt, bar_count,
                                     sample_minutes):
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
        freq = '{}T'.format(sample_minutes)

        log.info('creating data sample from bundle')
        df1 = self.data_portal.get_history_window(
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
            freq='{}T'.format(sample_minutes),
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


if __name__ == '__main__':
    exchanges = get_exchanges(['poloniex'])
    exchange = six.next(six.itervalues(exchanges))
    assets = exchange.get_assets(symbols=['eth_btc'])

    open_calendar = get_calendar('OPEN')
    asset_finder = AssetFinderExchange()
    data_portal = DataPortalExchangeBacktest(
        exchanges=exchanges,
        asset_finder=asset_finder,
        trading_calendar=open_calendar,
        first_trading_day=None  # will set dynamically based on assets
    )
    validator = Validator(data_portal=data_portal)

    validator.compare_bundle_with_exchange(
        exchange=exchange,
        assets=assets,
        end_dt=pd.to_datetime('2017-11-10 1:00', utc=True),
        bar_count=200,
        sample_minutes=30
    )
