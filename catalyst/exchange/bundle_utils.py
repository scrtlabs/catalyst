import calendar
import os
import tarfile
from datetime import timedelta, datetime, date

import numpy as np
import pandas as pd
import pytz

from catalyst.data.bundles import from_bundle_ingest_dirname
from catalyst.data.bundles.core import download_without_progress
from catalyst.exchange.exchange_errors import NoDataAvailableOnExchange
from catalyst.exchange.exchange_utils import get_exchange_bundles_folder
from catalyst.utils.deprecate import deprecated
from catalyst.utils.paths import data_path

EXCHANGE_NAMES = ['bitfinex', 'bittrex', 'poloniex']
API_URL = 'http://data.enigma.co/api/v1'


def get_date_from_ms(ms):
    return datetime.fromtimestamp(ms / 1000.0)


def get_seconds_from_date(date):
    epoch = datetime.utcfromtimestamp(0)
    epoch = epoch.replace(tzinfo=pytz.UTC)

    return int((date - epoch).total_seconds())


def get_bcolz_chunk(exchange_name, symbol, data_frequency, period):
    """
    Download and extract a bcolz bundle.

    :param exchange_name:
    :param symbol:
    :param data_frequency:
    :param period:
    :return:

    Note:
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
    return timedelta(minutes=periods) \
        if data_frequency == 'minute' else timedelta(days=periods)


def get_periods_range(start_dt, end_dt, data_frequency):
    freq = 'T' if data_frequency == 'minute' else 'D'

    return pd.date_range(start_dt, end_dt, freq=freq)


def get_periods(start_dt, end_dt, data_frequency):
    delta = end_dt - start_dt

    if data_frequency == 'minute':
        delta_periods = delta.total_seconds() / 60

    elif data_frequency == 'daily':
        delta_periods = delta.total_seconds() / 60 / 60 / 24

    else:
        raise ValueError('frequency not supported')

    return int(delta_periods)


def get_start_dt(end_dt, bar_count, data_frequency):
    periods = bar_count
    if periods > 1:
        delta = get_delta(periods, data_frequency)
        start_dt = end_dt - delta
    else:
        start_dt = end_dt

    return start_dt




def get_month_start_end(dt):
    """
    Returns the first and last day of the month for the specified date.

    :param dt:
    :return:
    """
    month_range = calendar.monthrange(dt.year, dt.month)
    month_start = pd.to_datetime(datetime(
        dt.year, dt.month, 1, 0, 0, 0, 0
    ), utc=True)

    month_end = pd.to_datetime(datetime(
        dt.year, dt.month, month_range[1], 23, 59, 0, 0
    ), utc=True)

    return month_start, month_end


def get_year_start_end(dt):
    """
    Returns the first and last day of the year for the specified date.

    :param dt:
    :return:
    """
    year_start = pd.to_datetime(date(dt.year, 1, 1), utc=True)
    year_end = pd.to_datetime(date(dt.year, 12, 31), utc=True)

    return year_start, year_end


def get_df_from_arrays(arrays, periods):
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

    :param asset:
    :param start_dt:
    :param end_dt:
    :param reader:
    :return:
    """
    has_data = True
    if has_data and reader is not None:
        try:
            start_close = \
                reader.get_value(asset.sid, start_dt, 'close')

            if np.isnan(start_close):
                has_data = False

            else:
                end_close = reader.get_value(asset.sid, end_dt, 'close')

                if np.isnan(end_close):
                    has_data = False

        except Exception as e:
            has_data = False

    else:
        has_data = False

    return has_data


@deprecated
def find_most_recent_time(bundle_name):
    """
    Find most recent "time folder" for a given bundle.

    :param bundle_name:
        The name of the targeted bundle.

    :return folder:
        The name of the time folder.
    """
    try:
        bundle_folders = os.listdir(
            data_path([bundle_name]),
        )
    except OSError:
        return None

    most_recent_bundle = dict()
    for folder in bundle_folders:
        date = from_bundle_ingest_dirname(folder)
        if not most_recent_bundle or date > \
                most_recent_bundle[list(most_recent_bundle.keys())[0]]:
            most_recent_bundle = dict()
            most_recent_bundle[folder] = date

    if most_recent_bundle:
        return list(most_recent_bundle.keys())[0]
    else:
        return None

