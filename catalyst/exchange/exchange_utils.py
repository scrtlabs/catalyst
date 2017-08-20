import os
import urllib
import json
from catalyst.utils.paths import data_root, ensure_directory
from catalyst.exchange.exchange_errors import ExchangeAuthNotFound, \
    ExchangeSymbolsNotFound

SYMBOLS_URL = 'https://raw.githubusercontent.com/enigmampc/catalyst/' \
              'live-trading/catalyst/exchange/symbols/{exchange}.json'


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
