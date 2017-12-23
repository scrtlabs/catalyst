import hashlib
import json
import os
import pickle
import re
import shutil
from datetime import date, datetime

import pandas as pd
from catalyst.assets._assets import TradingPair
from six import string_types
from six.moves.urllib import request

from catalyst.constants import DATE_FORMAT, SYMBOLS_URL
from catalyst.exchange.exchange_errors import ExchangeSymbolsNotFound, \
    InvalidHistoryFrequencyError, InvalidHistoryFrequencyAlias
from catalyst.utils.paths import data_root, ensure_directory, \
    last_modified_time


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


def get_exchange_symbols_filename(exchange_name, is_local=False, environ=None):
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
    name = 'symbols.json' if not is_local else 'symbols_local.json'
    exchange_folder = get_exchange_folder(exchange_name, environ)
    return os.path.join(exchange_folder, name)


def download_exchange_symbols(exchange_name, environ=None):
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
    filename = get_exchange_symbols_filename(exchange_name)
    url = SYMBOLS_URL.format(exchange=exchange_name)
    response = request.urlretrieve(url=url, filename=filename)
    return response


def symbols_parser(asset_def):
    for key, value in asset_def.items():
        match = isinstance(value, string_types) \
                and re.search(r'(\d{4}-\d{2}-\d{2})', value)

        if match:
            try:
                asset_def[key] = pd.to_datetime(value, utc=True)
            except ValueError:
                pass

    return asset_def


def get_exchange_symbols(exchange_name, is_local=False, environ=None):
    """
    The de-serialized content of the exchange's symbols.json.

    Parameters
    ----------
    exchange_name: str
    is_local: bool
    environ:

    Returns
    -------
    Object

    """
    filename = get_exchange_symbols_filename(exchange_name, is_local)

    if not is_local and (not os.path.isfile(filename) or pd.Timedelta(
                pd.Timestamp('now', tz='UTC') - last_modified_time(
                filename)).days > 1):
        download_exchange_symbols(exchange_name, environ)

    if os.path.isfile(filename):
        with open(filename) as data_file:
            try:
                data = json.load(data_file, object_hook=symbols_parser)
                return data

            except ValueError:
                return dict()
    else:
        raise ExchangeSymbolsNotFound(
            exchange=exchange_name,
            filename=filename
        )


def save_exchange_symbols(exchange_name, assets, is_local=False, environ=None):
    """
    Save assets into an exchange_symbols file.

    Parameters
    ----------
    exchange_name: str
    assets: list[dict[str, object]]
    is_local: bool
    environ

    Returns
    -------

    """
    asset_dicts = dict()
    for symbol in assets:
        asset_dicts[symbol] = assets[symbol].to_dict()

    filename = get_exchange_symbols_filename(
        exchange_name, is_local, environ
    )
    with open(filename, 'wt') as handle:
        json.dump(asset_dicts, handle, indent=4, default=symbols_serial)


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


def get_algo_object(algo_name, key, environ=None, rel_path=None):
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

    filename = os.path.join(folder, key + '.p')

    if os.path.isfile(filename):
        try:
            with open(filename, 'rb') as handle:
                return pickle.load(handle)
        except Exception:
            return None
    else:
        return None


def save_algo_object(algo_name, key, obj, environ=None, rel_path=None):
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

    filename = os.path.join(folder, key + '.p')

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


def symbols_serial(obj):
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
        return obj.floor('1D').strftime(DATE_FORMAT)

    raise TypeError("Type %s not serializable" % type(obj))


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


def mixin_market_params(exchange_name, params, market):
    """
    Applies a CCXT market dict to parameters of TradingPair init.

    Parameters
    ----------
    params: dict[Object]
    market: dict[Object]

    Returns
    -------

    """
    # TODO: make this more externalized / configurable
    if 'lot' in market:
        params['min_trade_size'] = market['lot']
        params['lot'] = market['lot']

    if exchange_name == 'bitfinex':
        params['maker'] = 0.001
        params['taker'] = 0.002

    elif 'maker' in market and 'taker' in market \
            and market['maker'] is not None and market['taker'] is not None:
        params['maker'] = market['maker']
        params['taker'] = market['taker']

    else:
        # TODO: default commission, make configurable
        params['maker'] = 0.0015
        params['taker'] = 0.0025

    info = market['info'] if 'info' in market else None
    if info:
        if 'minimum_order_size' in info:
            params['min_trade_size'] = float(info['minimum_order_size'])

            if 'lot' not in params:
                params['lot'] = params['min_trade_size']


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
