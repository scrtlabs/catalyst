import tarfile
import shutil

import requests
from datetime import timedelta, datetime
import os
from logging import Logger
import pandas as pd
import numpy as np

import pytz

from catalyst.data.bundles import from_bundle_ingest_dirname
from catalyst.data.bundles.core import download_without_progress
from catalyst.exchange.exchange_errors import ApiCandlesError
from catalyst.exchange.exchange_utils import get_exchange_bundles_folder
from catalyst.utils.deprecate import deprecated
from catalyst.utils.paths import data_path

log = Logger('test_exchange_bundle')

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


def get_ffill_candles(candles, bar_count, end_dt, data_frequency,
                      previous_candle=None):
    """
    Create candles for each period of the specified range, forward-filling
    missing candles with the previous value.

    :param candles:
    :param bar_count:
    :param end_dt:
    :param data_frequency:
    :param previous_candle:

    :return:
    """
    all_dates = []
    all_candles = []

    start_dt = get_start_dt(end_dt, bar_count, data_frequency)
    date = start_dt

    while date <= end_dt:
        candle = next((
            candle for candle in candles if candle['last_traded'] == date
        ), previous_candle)

        if candle is None:
            candle = candles[0]

        all_dates.append(date)
        all_candles.append(candle)

        previous_candle = candle

        date += get_delta(1, data_frequency)

    return all_dates, all_candles


def get_trailing_candles_dt(asset, start_dt, end_dt, data_frequency):
    missing_start = None

    if asset.end_minute is not None and start_dt < asset.end_minute:
        if asset.end_minute < end_dt:
            delta = get_delta(1, data_frequency)

            missing_start = asset.end_minute + delta

    else:
        missing_start = start_dt

    return missing_start


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
                most_recent_bundle[most_recent_bundle.keys()[0]]:
            most_recent_bundle = dict()
            most_recent_bundle[folder] = date

    if most_recent_bundle:
        return most_recent_bundle.keys()[0]
    else:
        return None


@deprecated
def get_history(exchange_name, data_frequency, symbol, start=None, end=None):
    """
    History API provides OHLCV data for any of the supported exchanges up to yesterday.

    :param exchange_name: string
        Required: The name identifier of the exchange (e.g. bitfinex, bittrex, poloniex).
    :param data_frequency: string
        Required: The bar frequency (minute or daily)
    :param symbol: string
        Required: The trading pair symbol, using Catalyst naming convention
    :param start: datetime
        Optional: The start date.
    :param end: datetime
        Optional: The end date.

    :return ohlcv: list[dict[string, float]]
        Each row contains the following dictionary for the resulting bars:
        'ts'     : int, the timestamp in seconds
        'open'   : float
        'high'   : float
        'low'    : float
        'close'  : float
        'volume' : float

    Notes
    =====
    Using seconds for the start and end dates for ease of use in the
    function query parameters.

    Sometimes, one minute goes by without completing a trade of the given
    trading pair on the given exchange. To minimize the payload size, we
    don't return identical sequential bars. Post-processing code will
    forward fill missing bars outside of this function.
    """

    start_seconds = get_seconds_from_date(start) if start else None
    end_seconds = get_seconds_from_date(end) if end else None

    if exchange_name not in EXCHANGE_NAMES:
        raise ValueError(
            'get_history function only supports the following exchanges: {}'.format(
                list(EXCHANGE_NAMES)))

    if data_frequency != 'daily' and data_frequency != 'minute':
        raise ValueError(
            'get_history currently only supports daily and minute data.'
        )

    url = '{api_url}/candles?exchange={exchange}&market={symbol}&freq={data_frequency}'.format(
        api_url=API_URL,
        exchange=exchange_name,
        symbol=symbol,
        data_frequency=data_frequency,
    )

    if start_seconds:
        url += '&start={}'.format(start_seconds)

    if end_seconds:
        url += '&end={}'.format(end_seconds)

    try:
        response = requests.get(url)
    except Exception as e:
        raise ValueError(e)

    data = response.json()

    if 'error' in data:
        raise ApiCandlesError(error=data['error'])

    for candle in data:
        last_traded = pd.Timestamp.utcfromtimestamp(candle['ts'])
        last_traded = last_traded.replace(tzinfo=pytz.UTC)

        candle['last_traded'] = last_traded

    return data
