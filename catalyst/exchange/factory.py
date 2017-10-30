from catalyst.exchange.bitfinex.bitfinex import Bitfinex
from catalyst.exchange.bittrex.bittrex import Bittrex
from catalyst.exchange.exchange_errors import ExchangeNotFoundError
from catalyst.exchange.exchange_utils import get_exchange_auth
from catalyst.exchange.poloniex.poloniex import Poloniex


def get_exchange(exchange_name, base_currency=None):
    exchange_auth = get_exchange_auth(exchange_name)
    if exchange_name == 'bitfinex':
        return Bitfinex(
            key=exchange_auth['key'],
            secret=exchange_auth['secret'],
            base_currency=base_currency,
            portfolio=None
        )

    elif exchange_name == 'bittrex':
        return Bittrex(
            key=exchange_auth['key'],
            secret=exchange_auth['secret'],
            base_currency=base_currency,
            portfolio=None
        )

    elif exchange_name == 'poloniex':
        return Poloniex(
            key=exchange_auth['key'],
            secret=exchange_auth['secret'],
            base_currency=base_currency,
            portfolio=None
        )

    else:
        raise ExchangeNotFoundError(exchange_name=exchange_name)


def get_exchanges(exchange_names):
    exchanges = dict()
    for exchange_name in exchange_names:
        exchanges[exchange_name] = get_exchange(exchange_name)

    return exchanges
