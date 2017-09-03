import json
import os
import pickle
import urllib
from datetime import date, datetime

from catalyst.exchange.exchange_errors import ExchangeAuthNotFound, \
    ExchangeSymbolsNotFound
from catalyst.utils.paths import data_root, ensure_directory

SYMBOLS_URL = 'https://raw.githubusercontent.com/enigmampc/catalyst/' \
              'exchange-trading/catalyst/exchange/{exchange}/symbols.json'


def get_exchange_folder(exchange_name, environ=None):
    if not environ:
        environ = os.environ

    root = data_root(environ)
    exchange_folder = os.path.join(root, 'exchanges', exchange_name)
    ensure_directory(exchange_folder)

    return exchange_folder


def download_exchange_symbols(exchange_name, environ=None):
    exchange_folder = get_exchange_folder(exchange_name, environ)
    filename = os.path.join(exchange_folder, 'symbols.json')

    url = SYMBOLS_URL.format(exchange=exchange_name)
    response = urllib.urlretrieve(url=url, filename=filename)
    return response


def get_exchange_symbols(exchange_name, environ=None):
    exchange_folder = get_exchange_folder(exchange_name, environ)
    filename = os.path.join(exchange_folder, 'symbols.json')

    if not os.path.isfile(filename):
        download_exchange_symbols(exchange_name, environ)

    if os.path.isfile(filename):
        with open(filename) as data_file:
            data = json.load(data_file)
            return data
    else:
        raise ExchangeSymbolsNotFound(
            exchange=exchange_name,
            filename=filename
        )


def get_exchange_auth(exchange_name, environ=None):
    exchange_folder = get_exchange_folder(exchange_name, environ)
    filename = os.path.join(exchange_folder, 'auth.json')

    if os.path.isfile(filename):
        with open(filename) as data_file:
            data = json.load(data_file)
            return data
    else:
        raise ExchangeAuthNotFound(
            exchange=exchange_name,
            filename=filename
        )


def get_algo_folder(algo_name, environ=None):
    if not environ:
        environ = os.environ

    root = data_root(environ)
    algo_folder = os.path.join(root, 'live_algos', algo_name)
    ensure_directory(algo_folder)

    return algo_folder


def get_algo_object(algo_name, key, environ=None, rel_path=None):
    folder = get_algo_folder(algo_name, environ)

    if rel_path is not None:
        folder = os.path.join(folder, rel_path)

    filename = os.path.join(folder, key + '.p')

    if os.path.isfile(filename):
        try:
            with open(filename, 'rb') as handle:
                return pickle.load(handle)
        except Exception as e:
            return None
    else:
        return None


def save_algo_object(algo_name, key, obj, environ=None, rel_path=None):
    folder = get_algo_folder(algo_name, environ)

    if rel_path is not None:
        folder = os.path.join(folder, rel_path)
        ensure_directory(folder)

    filename = os.path.join(folder, key + '.p')

    with open(filename, 'wb') as handle:
        pickle.dump(obj, handle, protocol=pickle.HIGHEST_PROTOCOL)


def append_algo_object(algo_name, key, obj, environ=None):
    algo_folder = get_algo_folder(algo_name, environ)
    filename = os.path.join(algo_folder, key + '.p')

    mode = 'a+b' if os.path.isfile(filename) else 'wb'
    with open(filename, mode) as handle:
        pickle.dump(obj, handle, protocol=pickle.HIGHEST_PROTOCOL)


def get_exchange_minute_writer_root(exchange_name, environ=None):
    exchange_folder = get_exchange_folder(exchange_name, environ)

    minute_data_folder = os.path.join(exchange_folder, 'minute_data')
    ensure_directory(minute_data_folder)

    return minute_data_folder


def perf_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))
