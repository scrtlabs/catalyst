import os

from catalyst.exchange.ccxt.ccxt_exchange import CCXT
from catalyst.exchange.exchange_errors import ExchangeAuthEmpty
from catalyst.exchange.exchange_utils import get_exchange_auth, \
    get_exchange_folder


def get_exchange(exchange_name, base_currency=None, portfolio=None,
                 must_authenticate=False):
    exchange_auth = get_exchange_auth(exchange_name)

    has_auth = (exchange_auth['key'] != '' and exchange_auth['secret'] != '')
    if must_authenticate and not has_auth:
        raise ExchangeAuthEmpty(
            exchange=exchange_name.title(),
            filename=os.path.join(
                get_exchange_folder(exchange_name), 'auth.json'
            )
        )

    return CCXT(
        exchange_name=exchange_name,
        key=exchange_auth['key'],
        secret=exchange_auth['secret'],
        base_currency=base_currency,
        portfolio=portfolio
    )


def get_exchanges(exchange_names):
    exchanges = dict()
    for exchange_name in exchange_names:
        exchanges[exchange_name] = get_exchange(exchange_name)

    return exchanges
