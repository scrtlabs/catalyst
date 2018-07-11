import json
import os
import random
from logging import Logger, WARNING
from time import sleep

import pandas as pd
from catalyst.assets._assets import TradingPair
from logbook import TestHandler

from catalyst.exchange.exchange_errors import ExchangeRequestError
from catalyst.exchange.exchange_execution import ExchangeLimitOrder
from catalyst.exchange.utils.exchange_utils import get_exchange_folder
from catalyst.exchange.utils.test_utils import select_random_exchanges, \
    handle_exchange_error, select_random_assets
from catalyst.testing import CatalystTestCase
from catalyst.testing.fixtures import WithLogger
from catalyst.exchange.utils.factory import get_exchanges, get_exchange

log = Logger('TestSuiteExchange')


class TestSuiteExchange(WithLogger, CatalystTestCase):
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
                print(
                    're-trying an exchange request {} {}'.format(
                        exchange.name, attempts
                    )
                )
                self._test_markets_exchange(exchange, attempts + 1)

        except Exception as e:
            handle_exchange_error(exchange, e)

        return assets

    def _test_markets(self):
        population = 3
        results = dict()

        exchanges = select_random_exchanges(population)  # Type: list[Exchange]
        for exchange in exchanges:
            assets = self._test_markets_exchange(exchange)

            if assets is not None:
                results[exchange.name] = len(assets)

                folder = get_exchange_folder(exchange.name)
                filename = os.path.join(folder, 'whitelist.json')

                symbols = [asset.symbol for asset in assets]
                with open(filename, 'wt') as handle:
                    json.dump(symbols, handle, indent=4)

        series = pd.Series(results)
        print('the tested markets\n{}'.format(series))

        if population is not None:
            assert (len(results) == population)

        pass

    def test_tickers(self):
        exchange_population = 3
        asset_population = 15

        # exchanges = select_random_exchanges(
        #     exchange_population,
        #     features=['fetchTickers'],
        # )  # Type: list[Exchange]
        exchanges = list(get_exchanges(['binance']).values())
        for exchange in exchanges:
            exchange.init()

            if exchange.assets and len(exchange.assets) >= asset_population:
                assets = select_random_assets(
                    exchange.assets, asset_population
                )
                tickers = exchange.tickers(assets)

                assert len(tickers) == asset_population

            else:
                print(
                    'skipping exchange without assets {}'.format(exchange.name)
                )
                exchange_population -= 1
        pass

    def test_candles(self):
        exchange_population = 3
        asset_population = 3

        # exchanges = select_random_exchanges(
        #     population=exchange_population,
        #     features=['fetchOHLCV'],
        # )  # Type: list[Exchange]
        exchanges = list(get_exchanges(['binance']).values())
        for exchange in exchanges:
            exchange.init()

            if exchange.assets and len(exchange.assets) >= asset_population:
                frequencies = exchange.get_candle_frequencies()
                freq = random.sample(frequencies, 1)[0]

                bar_count = random.randint(1, 10)
                end_dt = pd.Timestamp.utcnow().floor('1T')
                dt_range = pd.date_range(
                    end=end_dt, periods=bar_count, freq=freq
                )
                assets = select_random_assets(
                    exchange.assets, asset_population
                )

                candles = exchange.get_candles(
                    freq=freq,
                    assets=assets,
                    bar_count=bar_count,
                    start_dt=dt_range[0],
                )

                assert len(candles) == asset_population

            else:
                print(
                    'skipping exchange without assets {}'.format(exchange.name)
                )
                exchange_population -= 1
        pass

    def _test_orders(self):
        # population = 3
        quote_currency = 'eth'
        order_amount = 0.1

        # exchanges = select_random_exchanges(
        #     population=population,
        #     features=['fetchOrder'],
        #     is_authenticated=True,
        #     quote_currency=quote_currency,
        # )  # Type: list[Exchange]

        exchanges = [
            get_exchange(
                'binance',
                quote_currency=quote_currency,
                must_authenticate=True,
            )
        ]
        log_catcher = TestHandler()
        with log_catcher:
            for exchange in exchanges:
                exchange.init()

                assets = exchange.get_assets(quote_currency=quote_currency)
                asset = select_random_assets(assets, 1)[0]
                self.assertIsInstance(asset, TradingPair)

                tickers = exchange.tickers([asset])
                price = tickers[asset]['last_price']

                amount = order_amount / price

                limit_price = price * 0.8
                style = ExchangeLimitOrder(limit_price=limit_price)

                order = exchange.order(
                    asset=asset,
                    amount=amount,
                    style=style,
                )
                sleep(1)

                open_order = exchange.get_order(order.id, asset)
                self.assertEqual(0, open_order.status)

                exchange.cancel_order(open_order, asset)
                sleep(1)

                canceled_order = exchange.get_order(open_order.id, asset)
                warnings = [record for record in log_catcher.records if
                            record.level == WARNING]

                self.assertEqual(0, len(warnings))
                self.assertEqual(2, canceled_order.status)
                print(
                    'tested {exchange} / {symbol}, order: {order}'.format(
                        exchange=exchange.name,
                        symbol=asset.symbol,
                        order=order.id,
                    )
                )
        pass
