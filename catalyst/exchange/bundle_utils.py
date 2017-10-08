import datetime
import os
from logging import Logger

from catalyst.data.bundles import from_bundle_ingest_dirname
from catalyst.utils.paths import data_path

log = Logger('test_exchange_bundle')


def get_date_from_ms(ms):
    return datetime.datetime.fromtimestamp(ms / 1000.0)


def get_history_mock(exchange_name, data_frequency, symbol, start_ms, end_ms,
                     exchanges):
    """
    Mocking the history API written by Victor by proxying the request
    to Bitfinex.

    :param exchange_name: string
        The name identifier of the exchange (e.g. bitfinex).
        Only bitfinex is supported in this mock function.
    :param data_frequency: string
        The bar frequency (minute or daily)
    :param symbol: string
        The trading pair symbol.
    :param start_ms: float
        The start date in milliseconds.
    :param end_ms: float
        The end date in milliseconds.
    :param exchanges: MOCK ONLY
        This won't be required in production mode since the exchange object
        will be retrieved on the server.
    :return ohlcv: list[dict[string, float]]
        The open, high, low, volume collection for the resulting bars.

    Notes
    =====
    Using milliseconds for the start and end dates for ease of use in
    URL query parameters.

    Sometimes, one minute goes by without completing a trade of the given
    trading pair on the given exchange. To minimize the payload size, we
    don't return identical sequential bars. Post-processing code will
    forward fill missing bars outside of this function.
    """

    if exchange_name != 'bitfinex':
        raise ValueError('get_history mock function only works with bitfinex')

    exchange = exchanges[exchange_name]
    assets = [exchange.get_asset(symbol=symbol)]
    start = get_date_from_ms(start_ms)
    end = get_date_from_ms(end_ms)

    delta = end - start

    periods = delta.seconds % 3600 / 60.0 \
        if data_frequency == 'minute' else delta.days

    candles = exchange.get_candles(
        data_frequency=data_frequency,
        assets=assets,
        bar_count=periods,
        start_dt=start,
        end_dt=end
    )

    ohlcv = []
    for candle in candles:
        ohlcv.append(dict(
            open=candle['open'],
            high=candle['high'],
            low=candle['low'],
            close=candle['close'],
            volume=candle['volume'],
            last_traded=candle['last_traded']
        ))
    return ohlcv


def fetch_candles_chunk(exchange, assets, data_frequency, end_dt, bar_count):
    calc_start_dt = end_dt - datetime.timedelta(minutes=bar_count)
    candles = exchange.get_candles(
        data_frequency=data_frequency,
        assets=assets,
        bar_count=bar_count,
        start_dt=calc_start_dt,
        end_dt=end_dt
    )
    return candles

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
