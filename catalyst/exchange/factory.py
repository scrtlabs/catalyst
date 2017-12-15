import os

import ccxt
from logbook import Logger

from catalyst.constants import LOG_LEVEL
from catalyst.exchange.exchange import Exchange
from catalyst.exchange.ccxt.ccxt_exchange import CCXT
from catalyst.exchange.exchange_errors import ExchangeAuthEmpty
from catalyst.exchange.exchange_utils import get_exchange_auth, \
    get_exchange_folder, is_blacklist

log = Logger('factory', level=LOG_LEVEL)


def get_exchange(exchange_name, base_currency=None, must_authenticate=False,
                 skip_init=False):
    exchange_auth = get_exchange_auth(exchange_name)

    has_auth = (exchange_auth['key'] != '' and exchange_auth['secret'] != '')
    if must_authenticate and not has_auth:
        raise ExchangeAuthEmpty(
            exchange=exchange_name.title(),
            filename=os.path.join(
                get_exchange_folder(exchange_name), 'auth.json'
            )
        )

    exchange = CCXT(
        exchange_name=exchange_name,
        key=exchange_auth['key'],
        secret=exchange_auth['secret'],
        base_currency=base_currency,
    )

    if not skip_init:
        exchange.init()

    return exchange


def get_exchanges(exchange_names):
    exchanges = dict()
    for exchange_name in exchange_names:
        exchanges[exchange_name] = get_exchange(exchange_name)

    return exchanges


def find_exchanges(features=None, skip_blacklist=True):
    """
    Find exchanges filtered by a list of feature.

    Parameters
    ----------
    features: str
        The list of features.

    Returns
    -------
    list[Exchange]

    """
    exchange_names = CCXT.find_exchanges(features)

    exchanges = []
    for exchange_name in exchange_names:
        if skip_blacklist and is_blacklist(exchange_name):
            continue

        exchanges.append(get_exchange(exchange_name, skip_init=True))

    return exchanges
