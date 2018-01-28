import os

from catalyst.constants import LOG_LEVEL
from catalyst.exchange.ccxt.ccxt_exchange import CCXT
from catalyst.exchange.exchange import Exchange
from catalyst.exchange.exchange_errors import ExchangeAuthEmpty
from catalyst.exchange.utils.ccxt_utils import find_exchange_configs
from catalyst.exchange.utils.exchange_utils import get_exchange_auth, \
    get_exchange_folder
from logbook import Logger

log = Logger('factory', level=LOG_LEVEL)
exchange_cache = dict()


def get_exchange(exchange_name, base_currency=None, must_authenticate=False,
                 skip_init=False, auth_alias=None, config=None):
    key = (exchange_name, base_currency)
    if key in exchange_cache:
        return exchange_cache[key]

    exchange_auth = get_exchange_auth(exchange_name, alias=auth_alias)

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
        password=exchange_auth['password'] if 'password'
                                              in exchange_auth.keys() else '',
        base_currency=base_currency,
        config=config,
    )
    exchange_cache[key] = exchange

    if not skip_init:
        exchange.init()

    return exchange


def get_exchanges(exchange_names):
    exchanges = dict()
    for exchange_name in exchange_names:
        exchanges[exchange_name] = get_exchange(exchange_name)

    return exchanges


def find_exchanges(features=None, history=None, skip_blacklist=True, path=None,
                   is_authenticated=False, base_currency=None):
    """
    Find exchanges filtered by a list of feature.

    Parameters
    ----------
    features: str
        The list of features.

    skip_blacklist: bool
    is_authenticated: bool
    base_currency: bool

    Returns
    -------
    list[Exchange]

    """
    exchange_configs = find_exchange_configs(
        features, history, is_authenticated, path
    )
    exchanges = []
    for config in exchange_configs:
        if skip_blacklist and (config is None or 'error' in config):
            continue

        exchange = get_exchange(
            exchange_name=config['id'],
            skip_init=True,
            base_currency=base_currency,
            config=config,
        )
        exchanges.append(exchange)

    return exchanges
