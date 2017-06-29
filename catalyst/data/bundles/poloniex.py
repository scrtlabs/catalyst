import os
from datetime import datetime

import numpy as np
import pandas as pd
from pandas_datareader.data import DataReader
from pandas.tseries.offsets import DateOffset
import requests

from catalyst.utils.calendars import register_calendar_alias
from catalyst.utils.cli import maybe_show_progress
from .core import register


def _cachpath(symbol, type_):
    return '-'.join((symbol.replace(os.path.sep, '_'), type_))


def poloniex_cryptoassets(symbols, start=None, end=None):
    """Create a data bundle ingest function from a set of symbols loaded from
    poloniex

    Parameters
    ----------
    symbols : iterable[str]
        The ticker symbols to load data for.
    start : datetime, optional
        The start date to query for. By default this pulls the full history
        for the calendar.
    end : datetime, optional
        The end date to query for. By default this pulls the full history
        for the calendar.

    Returns
    -------
    ingest : callable
        The bundle ingest function for the given set of symbols.

    Examples
    --------
    This code should be added to ~/.catalyst/extension.py

    .. code-block:: python

       from catalyst.data.bundles import poloniex_cryptoassets, register

       symbols = (
           'USDT_BTC',
           'USDT_ETH',
           'USDT_LTC',
       )
       register('my_bundle', poloniex_cryptoassets(symbols))

    Notes
    -----
    The sids for each symbol will be the index into the symbols sequence.
    """
    # strict this in memory so that we can reiterate over it
    symbols = tuple(symbols)

    def ingest(environ,
               asset_db_writer,
               minute_bar_writer,  # unused
               daily_bar_writer,
               adjustment_writer,
               calendar,
               start_session,
               end_session,
               cache,
               show_progress,
               output_dir,
               # pass these as defaults to make them 'nonlocal' in py2
               start=start,
               end=end):
        if start is None:
            start = start_session
        if end is None:
            end = None

        metadata = pd.DataFrame(np.empty(len(symbols), dtype=[
            ('start_date', 'datetime64[ns]'),
            ('end_date', 'datetime64[ns]'),
            ('auto_close_date', 'datetime64[ns]'),
            ('symbol', 'object'),
        ]))

        day_offset = pd.Timedelta(days=1)

        def compute_daily_bars(five_min_bars):
            # filter and copy the entry at the beginning of each session
            daily_bars = five_min_bars[
                five_min_bars.index.isin(calendar.all_sessions)
            ].copy()

            # iterate through session starts doing:
            # 1. filter five_min_bars to get all entries in one day
            # 2. compute daily bar entry
            # 3. record in rid-th row of daily_bars
            for rid, start_date in enumerate(daily_bars.index):
                # compute beginning of next session
                end_date = start_date + day_offset

                # filter for entries session entries
                day_data = five_min_bars[
                    (five_min_bars.index >= start_date) &
                    (five_min_bars.index < end_date)
                ]

                # compute and record daily bar
                daily_bars.iloc[rid] = (
                    day_data.open.iloc[0],   # first open price
                    day_data.high.max(),     # max of high prices
                    day_data.low.min(),      # min of low prices
                    day_data.close.iloc[-1], # last close price
                    day_data.volume.sum(),   # sum of all volumes
                )

            # scale to allow trading 10-ths of a coin
            scale = 10.0
            daily_bars.loc[:, 'open'] /= scale
            daily_bars.loc[:, 'high'] /= scale
            daily_bars.loc[:, 'low'] /= scale
            daily_bars.loc[:, 'close'] /= scale
            daily_bars.loc[:, 'volume'] *= scale
            
            return daily_bars

        def _pricing_iter():
            sid = 0
            print 'Ingesting symbols: {0}'.format(symbols)
            with maybe_show_progress(
                symbols, 
                show_progress,
                show_percent=True,
                item_show_func=lambda s: 'building {0}'.format(s)
                                          if s is not None
                                          else 'DONE',
                info_sep=' | ',
                label='Compiling daily bar pricing datasets:',
             ) as it:

                for symbol in it:
                    #def to_dataframe(self, start, end, currencyPair=None):
                    csv_fn = '/var/tmp/catalyst/data/poloniex/crypto_prices-' +\
                        symbol + '.csv'

                    #last_date = self._get_start_date(csv_fn)
                    #if last_date + 300 < end or not os.path.exists(csv_fn):
                        # get latest data
                        #self.append_data_single_pair(currencyPair)

                    # CSV holds the latest snapshot
                    columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                    five_min_bars = pd.read_csv(csv_fn,  names=columns)
                    five_min_bars.set_index('date', inplace=True)
                    five_min_bars.index = pd.to_datetime(
                        five_min_bars.index,
                        utc=True,
                        unit='s',
                    )

                    daily_bars = compute_daily_bars(five_min_bars)

                    # the start date is the date of the first trade and
                    # the end date is the date of the last trade
                    start_date = daily_bars.index[0].tz_localize(None)
                    end_date = daily_bars.index[-1].tz_localize(None)
                    # The auto_close date is the day after the last trade.
                    ac_date = end_date + day_offset
                    metadata.iloc[sid] = start_date, end_date, ac_date, symbol

                    yield sid, daily_bars
                    sid += 1

        daily_bar_writer.write(
            _pricing_iter(),
            assets=metadata.symbol.index,
        )

        symbol_map = pd.Series(metadata.symbol.index, metadata.symbol)

        # Hardcode the exchange to "POLO" for all assets and (elsewhere)
        # register "POLO" to resolve to the OPEN calendar, because these are
        # all cryptoassets and thus use the OPEN calendar.
        metadata['exchange'] = 'POLO'
        asset_db_writer.write(equities=metadata)

        adjustment_writer.write()

    return ingest
    

# bundle used when creating test data
register(
    '.test-poloniex',
    poloniex_cryptoassets(
        (
            'USDT_BTC',
            'USDT_ETH',
            'USDT_LTC',
        ),
        pd.Timestamp('2010-01-01', tz='utc'),
        pd.Timestamp('2015-01-01', tz='utc'),
    ),
    calendar_name='OPEN',
    minutes_per_day=1440,
)
