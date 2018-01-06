import hashlib
import json
import os
import pickle
import re
import shutil
from datetime import date, datetime

import pandas as pd
from catalyst.assets._assets import TradingPair
from catalyst.constants import EXCHANGE_CONFIG_URL
from catalyst.exchange.exchange_errors import InvalidHistoryFrequencyError, \
    InvalidHistoryFrequencyAlias
from catalyst.exchange.utils.serialization_utils import ExchangeJSONEncoder, \
    ExchangeJSONDecoder, ConfigJSONEncoder
from catalyst.utils.paths import data_root, ensure_directory, \
    last_modified_time
from six import string_types
from six.moves.urllib import request


def get_sid(symbol):
    """
    Create a sid by hashing the symbol of a currency pair.

    Parameters
    ----------
    symbol: str

    Returns
    -------
    int
        The resulting sid.

    """
    sid = int(
        hashlib.sha256(symbol.encode('utf-8')).hexdigest(), 16
    ) % 10 ** 6
    return sid


def get_exchange_folder(exchange_name, environ=None):
    """
    The root path of an exchange folder.

    Parameters
    ----------
    exchange_name: str
    environ:

    Returns
    -------
    str

    """
    if not environ:
        environ = os.environ

    root = data_root(environ)
    exchange_folder = os.path.join(root, 'exchanges', exchange_name)
    ensure_directory(exchange_folder)

    return exchange_folder


def is_blacklist(exchange_name, environ=None):
    exchange_folder = get_exchange_folder(exchange_name, environ)
    filename = os.path.join(exchange_folder, 'blacklist.txt')

    return os.path.exists(filename)


def get_exchange_config_filename(exchange_name, environ=None):
    """
    The absolute path of the exchange's symbol.json file.

    Parameters
    ----------
    exchange_name:
    environ:

    Returns
    -------
    str

    """
    name = 'config.json'
    exchange_folder = get_exchange_folder(exchange_name, environ)
    return os.path.join(exchange_folder, name)


def download_exchange_config(exchange_name, filename, environ=None):
    """
    Downloads the exchange's symbols.json from the repository.

    Parameters
    ----------
    exchange_name: str
    environ:

    Returns
    -------
    str

    """
    url = EXCHANGE_CONFIG_URL.format(exchange=exchange_name)
    request.urlretrieve(url=url, filename=filename)


def get_exchange_config(exchange_name, filename=None, environ=None):
    """
    The de-serialized content of the exchange's config.json.

    Parameters
    ----------
    exchange_name: str
    is_local: bool
    environ:

    Returns
    -------
    Object

    """
    if filename is None:
        filename = get_exchange_config_filename(exchange_name)

    if os.path.isfile(filename):
        now = pd.Timestamp.utcnow()
        limit = pd.Timedelta('2H')
        if pd.Timedelta(now - last_modified_time(filename)) > limit:
            download_exchange_config(exchange_name, filename, environ)

    else:
        download_exchange_config(exchange_name, filename, environ)

    with open(filename) as data_file:
        try:
            data = json.load(data_file, cls=ExchangeJSONDecoder)
            return data

        except ValueError:
            return dict()

def save_exchange_config(exchange_name, config, filename=None, environ=None):
    """
    Save assets into an exchange_config file.

    Parameters
    ----------
    exchange_name: str
    config
    environ

    Returns
    -------

    """
    if filename is None:
        name = 'config.json'
        exchange_folder = get_exchange_folder(exchange_name, environ)
        filename = os.path.join(exchange_folder, name)

    with open(filename, 'w+') as handle:
        json.dump(config, handle, indent=4, cls=ConfigJSONEncoder)


def get_symbols_string(assets):
    """
    A concatenated string of symbols from a list of assets.

    Parameters
    ----------
    assets: list[TradingPair]

    Returns
    -------
    str

    """
    array = [assets] if isinstance(assets, TradingPair) else assets
    return ', '.join([asset.symbol for asset in array])


def get_exchange_auth(exchange_name, environ=None):
    """
    The de-serialized contend of the exchange's auth.json file.

    Parameters
    ----------
    exchange_name: str
    environ:

    Returns
    -------
    Object

    """
    exchange_folder = get_exchange_folder(exchange_name, environ)
    filename = os.path.join(exchange_folder, 'auth.json')

    if os.path.isfile(filename):
        with open(filename) as data_file:
            data = json.load(data_file)
            return data
    else:
        data = dict(name=exchange_name, key='', secret='')
        with open(filename, 'w') as f:
            json.dump(data, f, sort_keys=False, indent=2,
                      separators=(',', ':'))
            return data


def delete_algo_folder(algo_name, environ=None):
    """
    Delete the folder containing the algo state.

    Parameters
    ----------
    algo_name: str
    environ:

    Returns
    -------
    str

    """
    folder = get_algo_folder(algo_name, environ)
    shutil.rmtree(folder)


def get_algo_folder(algo_name, environ=None):
    """
    The algorithm root folder of the algorithm.

    Parameters
    ----------
    algo_name: str
    environ:

    Returns
    -------
    str

    """
    if not environ:
        environ = os.environ

    root = data_root(environ)
    algo_folder = os.path.join(root, 'live_algos', algo_name)
    ensure_directory(algo_folder)

    return algo_folder


def get_algo_object(algo_name, key, environ=None, rel_path=None, how='pickle'):
    """
    The de-serialized object of the algo name and key.

    Parameters
    ----------
    algo_name: str
    key: str
    environ:
    rel_path: str

    Returns
    -------
    Object

    """
    if algo_name is None:
        return None

    folder = get_algo_folder(algo_name, environ)

    if rel_path is not None:
        folder = os.path.join(folder, rel_path)

    name = '{}.p'.format(key) if how == 'pickle' else '{}.json'.format(key)
    filename = os.path.join(folder, name)

    if os.path.isfile(filename):
        if how == 'pickle':
            with open(filename, 'rb') as handle:
                return pickle.load(handle)

        else:
            with open(filename) as data_file:
                data = json.load(data_file, cls=ExchangeJSONDecoder)
                return data

    else:
        return None


def save_algo_object(algo_name, key, obj, environ=None, rel_path=None,
                     how='pickle'):
    """
    Serialize and save an object by algo name and key.

    Parameters
    ----------
    algo_name: str
    key: str
    obj: Object
    environ:
    rel_path: str

    """
    folder = get_algo_folder(algo_name, environ)

    if rel_path is not None:
        folder = os.path.join(folder, rel_path)
        ensure_directory(folder)

    if how == 'json':
        filename = os.path.join(folder, '{}.json'.format(key))
        with open(filename, 'wt') as handle:
            json.dump(obj, handle, indent=4, cls=ExchangeJSONEncoder)

    else:
        filename = os.path.join(folder, '{}.p'.format(key))
        with open(filename, 'wb') as handle:
            pickle.dump(obj, handle, protocol=pickle.HIGHEST_PROTOCOL)


def get_algo_df(algo_name, key, environ=None, rel_path=None):
    """
    The de-serialized DataFrame of an algo name and key.

    Parameters
    ----------
    algo_name: str
    key: str
    environ:
    rel_path: str

    Returns
    -------
    DataFrame

    """
    folder = get_algo_folder(algo_name, environ)

    if rel_path is not None:
        folder = os.path.join(folder, rel_path)

    filename = os.path.join(folder, key + '.csv')

    if os.path.isfile(filename):
        try:
            with open(filename, 'rb') as handle:
                return pd.read_csv(handle, index_col=0, parse_dates=True)
        except IOError:
            return pd.DataFrame()
    else:
        return pd.DataFrame()


def save_algo_df(algo_name, key, df, environ=None, rel_path=None):
    """
    Serialize to csv and save a DataFrame by algo name and key.

    Parameters
    ----------
    algo_name: str
    key: str
    df: pd.DataFrame
    environ:
    rel_path: str

    """
    folder = get_algo_folder(algo_name, environ)
    if rel_path is not None:
        folder = os.path.join(folder, rel_path)
        ensure_directory(folder)

    filename = os.path.join(folder, key + '.csv')

    with open(filename, 'wt') as handle:
        df.to_csv(handle, encoding='UTF_8')


def get_exchange_minute_writer_root(exchange_name, environ=None):
    """
    The minute writer folder for the exchange.

    Parameters
    ----------
    exchange_name: str
    environ:

    Returns
    -------
    BcolzExchangeBarWriter

    """
    exchange_folder = get_exchange_folder(exchange_name, environ)

    minute_data_folder = os.path.join(exchange_folder, 'minute_data')
    ensure_directory(minute_data_folder)

    return minute_data_folder


def get_exchange_bundles_folder(exchange_name, environ=None):
    """
    The temp folder for bundle downloads by algo name.

    Parameters
    ----------
    exchange_name: str
    environ:

    Returns
    -------
    str

    """
    exchange_folder = get_exchange_folder(exchange_name, environ)

    temp_bundles = os.path.join(exchange_folder, 'temp_bundles')
    ensure_directory(temp_bundles)

    return temp_bundles


def has_bundle(exchange_name, data_frequency, environ=None):
    exchange_folder = get_exchange_folder(exchange_name, environ)

    folder_name = '{}_bundle'.format(data_frequency.lower())
    folder = os.path.join(exchange_folder, folder_name)

    return os.path.isdir(folder)


def perf_serial(obj):
    """
    JSON serializer for objects not serializable by default json code

    Parameters
    ----------
    obj: Object

    Returns
    -------
    str

    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    raise TypeError("Type %s not serializable" % type(obj))


def get_common_assets(exchanges):
    """
    The assets available in all specified exchanges.

    Parameters
    ----------
    exchanges: list[Exchange]

    Returns
    -------
    list[TradingPair]

    """
    symbols = []
    for exchange_name in exchanges:
        s = [asset.symbol for asset in exchanges[exchange_name].get_assets()]
        symbols.append(s)

    inter_symbols = set.intersection(*map(set, symbols))

    assets = []
    for symbol in inter_symbols:
        for exchange_name in exchanges:
            asset = exchanges[exchange_name].get_asset(symbol)
            assets.append(asset)

    return assets


def get_frequency(freq, data_frequency):
    """
    Get the frequency parameters.

    Notes
    -----
    We're trying to use Pandas convention for frequency aliases.

    Parameters
    ----------
    freq: str
    data_frequency: str

    Returns
    -------
    str, int, str, str

    """
    if freq == 'minute':
        unit = 'T'
        candle_size = 1

    elif freq == 'daily':
        unit = 'D'
        candle_size = 1

    else:
        freq_match = re.match(r'([0-9].*)?(m|M|d|D|h|H|T)', freq, re.M | re.I)
        if freq_match:
            candle_size = int(freq_match.group(1)) if freq_match.group(1) \
                else 1
            unit = freq_match.group(2)

        else:
            raise InvalidHistoryFrequencyError(frequency=freq)

    # TODO: some exchanges support H and W frequencies but not bundles
    # Find a way to pass-through these parameters to exchanges
    # but resample from minute or daily in backtest mode
    # see catalyst/exchange/ccxt/ccxt_exchange.py:242 for mapping between
    # Pandas offet aliases (used by Catalyst) and the CCXT timeframes
    if unit.lower() == 'd':
        alias = '{}D'.format(candle_size)

        if data_frequency == 'minute':
            data_frequency = 'daily'

    elif unit.lower() == 'm' or unit == 'T':
        alias = '{}T'.format(candle_size)

        if data_frequency == 'daily':
            data_frequency = 'minute'

    # elif unit.lower() == 'h':
    #     candle_size = candle_size * 60
    #
    #     alias = '{}T'.format(candle_size)
    #     if data_frequency == 'daily':
    #         data_frequency = 'minute'

    else:
        raise InvalidHistoryFrequencyAlias(freq=freq)

    return alias, candle_size, unit, data_frequency


def resample_history_df(df, freq, field):
    """
    Resample the OHCLV DataFrame using the specified frequency.

    Parameters
    ----------
    df: DataFrame
    freq: str
    field: str

    Returns
    -------
    DataFrame

    """
    if field == 'open':
        agg = 'first'
    elif field == 'high':
        agg = 'max'
    elif field == 'low':
        agg = 'min'
    elif field == 'close':
        agg = 'last'
    elif field == 'volume':
        agg = 'sum'
    else:
        raise ValueError('Invalid field.')

    resampled_df = df.resample(freq).agg(agg)
    return resampled_df


def from_ms_timestamp(ms):
    return pd.to_datetime(ms, unit='ms', utc=True)


def get_epoch():
    return pd.to_datetime('1970-1-1', utc=True)


def group_assets_by_exchange(assets):
    exchange_assets = dict()
    for asset in assets:
        if asset.exchange not in exchange_assets:
            exchange_assets[asset.exchange] = list()

        exchange_assets[asset.exchange].append(asset)

    return exchange_assets


def get_catalyst_symbol(market_or_symbol):
    """
    The Catalyst symbol.

    Parameters
    ----------
    market_or_symbol

    Returns
    -------

    """
    if isinstance(market_or_symbol, string_types):
        parts = market_or_symbol.split('/')
        return '{}_{}'.format(parts[0].lower(), parts[1].lower())

    else:
        return '{}_{}'.format(
            market_or_symbol['base'].lower(),
            market_or_symbol['quote'].lower(),
        )


def save_asset_data(folder, df, decimals=8):
    symbols = df.index.get_level_values('symbol')
    for symbol in symbols:
        symbol_df = df.loc[(symbols == symbol)]  # Type: pd.DataFrame

        filename = os.path.join(folder, '{}.csv'.format(symbol))
        if os.path.exists(filename):
            print_headers = False

        else:
            print_headers = True

        with open(filename, 'a') as f:
            symbol_df.to_csv(
                path_or_buf=f,
                header=print_headers,
                float_format='%.{}f'.format(decimals),
            )


def get_candles_df(candles, field, freq, bar_count, end_dt,
                   previous_value=None):
    all_series = dict()
    for asset in candles:
        periods = pd.date_range(end=end_dt, periods=bar_count, freq=freq)

        dates = [candle['last_traded'] for candle in candles[asset]]
        values = [candle[field] for candle in candles[asset]]
        series = pd.Series(values, index=dates)

        series = series.reindex(
            periods,
            method='ffill',
            fill_value=previous_value,
        )
        series.sort_index(inplace=True)
        all_series[asset] = series

    df = pd.DataFrame(all_series)
    df.dropna(inplace=True)

    return df
