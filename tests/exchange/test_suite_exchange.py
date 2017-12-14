import json
import os
import random
import unittest
from logging import Logger
from time import sleep

import pandas as pd
from ccxt import AuthenticationError

from catalyst.exchange.exchange_errors import ExchangeRequestError
from catalyst.exchange.exchange_utils import get_exchange_folder
from catalyst.exchange.factory import find_exchanges
from catalyst.utils.paths import data_root

log = Logger('TestSuiteExchange')


def handle_exchange_error(exchange, e):
    is_blacklist = False

    if isinstance(e, AuthenticationError):
        is_blacklist = True

    elif isinstance(e, ValueError) or isinstance(e, ExchangeRequestError):
        is_blacklist = True

    else:
        log.warn('unexpected error: {}'.format(e))
        is_blacklist = True

    if is_blacklist:
        root = data_root()
        filename = os.path.join(root, 'exchanges', 'blacklist.json')

        if os.path.isfile(filename):
            with open(filename) as handle:
                try:
                    bl_data = json.load(handle)

                except ValueError:
                    bl_data = dict()

        else:
            bl_data = dict()

        if exchange.name not in bl_data:
            bl_data[exchange.name] = '{}: {}'.format(e.__class__, e.message)
            with open(filename, 'wt') as handle:
                json.dump(bl_data, handle, indent=4)


def select_random_exchanges(population=3, features=None):
    all_exchanges = find_exchanges(features)

    if population is not None:
        exchanges = random.sample(all_exchanges, population)

    else:
        exchanges = all_exchanges

    return exchanges


def select_random_assets(exchange, population=3):
    all_assets = exchange.assets
    assets = random.sample(all_assets, population)
    return assets


# TODO: convert to Nosetest
class TestSuiteExchange(unittest.TestCase):
    def _test_markets_exchange(self, exchange, attempts=0):
        assets = None
        try:
            exchange.init()

            # Verify that the assets and markets are populated
            if not exchange.markets:
                raise ValueError(
                    'no markets found'
                )
            if not exchange.assets:
                raise ValueError(
                    'no assets derived from markets'
                )
            assets = exchange.assets

        except ExchangeRequestError as e:
            sleep(5)

            if attempts > 5:
                handle_exchange_error(exchange, e)

            else:
                self._test_markets_exchange(exchange, attempts + 1)

        except Exception as e:
            handle_exchange_error(exchange, e)

        return assets

    def test_markets(self):
        population = None
        results = dict()

        exchanges = select_random_exchanges(population)  # Type: list[Exchange]
        for exchange in exchanges:
            assets = self._test_markets_exchange(exchange)
            if assets is not None:
                results[exchange.name] = len(assets)

                folder = get_exchange_folder(exchange.name)
                filename = os.path.join(folder, 'supported_assets.json')

                symbols = [asset.symbol for asset in assets]
                with open(filename, 'wt') as handle:
                    json.dump(symbols, handle, indent=4)

        series = pd.Series(results)
        print('the tested markets\n{}'.format(series))

        if population is not None:
            assert (len(results) == population)

        pass

    def test_ticker(self):
        exchanges = select_random_exchanges(3)  # Type: list[Exchange]
        for exchange in exchanges:
            exchange.init()

            assets = select_random_assets(exchange, 3)
            exchange.tickers()
        pass

    def test_candles(self):
        pass

    def test_orders(self):
        pass
