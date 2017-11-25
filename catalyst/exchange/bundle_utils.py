import calendar
import os
import tarfile
from datetime import timedelta, datetime, date

import numpy as np
import pandas as pd
import pytz
from catalyst.assets._assets import TradingPair

from catalyst.data.bundles.core import download_without_progress
from catalyst.exchange.exchange_utils import get_exchange_bundles_folder, \
    get_exchange_symbols

EXCHANGE_NAMES = ['bitfinex', 'bittrex', 'poloniex']
API_URL = 'http://data.enigma.co/api/v1'


def get_date_from_ms(ms):
    """
    The date from the number of miliseconds from the epoch.

    Parameters
    ----------
    ms: int

    Returns
    -------
    datetime

    """
    return datetime.fromtimestamp(ms / 1000.0)


def get_seconds_from_date(date):
    """
    The number of seconds from the epoch.

    Parameters
    ----------
    date: datetime

    Returns
    -------
    int

    """
    epoch = datetime.utcfromtimestamp(0)
    epoch = epoch.replace(tzinfo=pytz.UTC)

    return int((date - epoch).total_seconds())


def get_bcolz_chunk(exchange_name, symbol, data_frequency, period):
    """
    Download and extract a bcolz bundle.

    Parameters
    ----------
    exchange_name: str
    symbol: str
    data_frequency: str
    period: str

    Returns
    -------
    str
        Filename: bitfinex-daily-neo_eth-2017-10.tar.gz

    """
    root = get_exchange_bundles_folder(exchange_name)
    name = '{exchange}-{frequency}-{symbol}-{period}'.format(
        exchange=exchange_name,
        frequency=data_frequency,
        symbol=symbol,
        period=period
    )
    path = os.path.join(root, name)

    if not os.path.isdir(path):
        url = 'https://s3.amazonaws.com/enigmaco/catalyst-bundles/' \
              'exchange-{exchange}/{name}.tar.gz'.format(
            exchange=exchange_name,
            name=name
        )

        bytes = download_without_progress(url)
        with tarfile.open('r', fileobj=bytes) as tar:
            tar.extractall(path)

    return path


def get_delta(periods, data_frequency):
    """
    Get a time delta based on the specified data frequency.

    Parameters
    ----------
    periods: int
    data_frequency: str

    Returns
    -------
    timedelta

    """
    return timedelta(minutes=periods) \
        if data_frequency == 'minute' else timedelta(days=periods)


def get_periods_range(start_dt, end_dt, freq):
    """
    Get a date range for the specified parameters.

    Parameters
    ----------
    start_dt: datetime
    end_dt: datetime
    freq: str

    Returns
    -------
    DateTimeIndex

    """
    if freq == 'minute':
        freq = 'T'

    elif freq == 'daily':
        freq = 'D'

    return pd.date_range(start_dt, end_dt, freq=freq)


def get_periods(start_dt, end_dt, freq):
    """
    The number of periods in the specified range.

    Parameters
    ----------
    start_dt: datetime
    end_dt: datetime
    freq: str

    Returns
    -------
    int

    """
    return len(get_periods_range(start_dt, end_dt, freq))


def get_start_dt(end_dt, bar_count, data_frequency, include_first=True):
    """
    The start date based on specified end date and data frequency.

    Parameters
    ----------
    end_dt: datetime
    bar_count: int
    data_frequency: str

    Returns
    -------
    datetime

    """
    periods = bar_count
    if periods > 1:
        delta = get_delta(periods, data_frequency)
        start_dt = end_dt - delta

        if not include_first:
            start_dt += get_delta(1, data_frequency)
    else:
        start_dt = end_dt

    return start_dt


def get_period_label(dt, data_frequency):
    """
    The period label for the specified date and frequency.

    Parameters
    ----------
    dt: datetime
    data_frequency: str

    Returns
    -------
    str

    """
    return '{}-{:02d}'.format(dt.year, dt.month) if data_frequency == 'minute' \
        else '{}'.format(dt.year)


def get_month_start_end(dt, first_day=None, last_day=None):
    """
    The first and last day of the month for the specified date.

    Parameters
    ----------
    dt: datetime
    first_day: datetime
    last_day: datetime

    Returns
    -------
    datetime, datetime

    """
    month_range = calendar.monthrange(dt.year, dt.month)

    if first_day:
        month_start = first_day
    else:
        month_start = pd.to_datetime(datetime(
            dt.year, dt.month, 1, 0, 0, 0, 0
        ), utc=True)

    if last_day:
        month_end = last_day
    else:
        month_end = pd.to_datetime(datetime(
            dt.year, dt.month, month_range[1], 23, 59, 0, 0
        ), utc=True)

        if month_end > pd.Timestamp.utcnow():
            month_end = pd.Timestamp.utcnow().floor('1D')

    return month_start, month_end


def get_year_start_end(dt, first_day=None, last_day=None):
    """
    The first and last day of the year for the specified date.

    Parameters
    ----------

    dt: datetime
    first_day: datetime
    last_day: datetime

    Returns
    -------
    datetime, datetime

    """
    year_start = first_day if first_day \
        else pd.to_datetime(date(dt.year, 1, 1), utc=True)
    year_end = last_day if last_day \
        else pd.to_datetime(date(dt.year, 12, 31), utc=True)

    if year_end > pd.Timestamp.utcnow():
        year_end = pd.Timestamp.utcnow().floor('1D')

    return year_start, year_end


def get_df_from_arrays(arrays, periods):
    """
    A DataFrame from the specified OHCLV arrays.

    Parameters
    ----------
    arrays: Object
    periods: DateTimeIndex

    Returns
    -------
    DataFrame

    """
    ohlcv = dict()
    for index, field in enumerate(
            ['open', 'high', 'low', 'close', 'volume']):
        ohlcv[field] = arrays[index].flatten()

    df = pd.DataFrame(
        data=ohlcv,
        index=periods
    )
    return df


def range_in_bundle(asset, start_dt, end_dt, reader):
    """
    Evaluate whether price data of an asset is included has been ingested in
    the exchange bundle for the given date range.

    Parameters
    ----------
    asset: TradingPair
    start_dt: datetime
    end_dt: datetime
    reader: BcolzBarMinuteReader

    Returns
    -------
    bool

    """
    has_data = True
    dates = [start_dt, end_dt]

    while dates and has_data:
        try:
            dt = dates.pop(0)
            close = reader.get_value(asset.sid, dt, 'close')

            if np.isnan(close):
                has_data = False

        except Exception as e:
            has_data = False

    return has_data


def get_assets(exchange, include_symbols, exclude_symbols):
    """
    Get assets from an exchange, including or excluding the specified
    symbols.

    Parameters
    ----------
    exchange: Exchange
    include_symbols: str
    exclude_symbols: str

    Returns
    -------
    list[TradingPair]

    """
    if include_symbols is not None:
        include_symbols_list = include_symbols.split(',')

        return exchange.get_assets(include_symbols_list)

    else:
        all_assets = exchange.get_assets()

        if exclude_symbols is not None:
            exclude_symbols_list = exclude_symbols.split(',')

            assets = []
            for asset in all_assets:
                if asset.symbol not in exclude_symbols_list:
                    assets.append(asset)

            return assets

        else:
            return all_assets
