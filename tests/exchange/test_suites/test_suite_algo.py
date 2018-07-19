import importlib

import pandas as pd
import os

from catalyst import run_algorithm
from catalyst.constants import ALPHA_WARNING_MESSAGE

from catalyst.exchange.utils.stats_utils import get_pretty_stats, \
    extract_transactions, set_print_settings, extract_orders
from catalyst.exchange.utils.test_utils import clean_exchange_bundles, \
    ingest_exchange_bundles

from catalyst.testing.fixtures import WithLogger, CatalystTestCase
from logbook import TestHandler, WARNING

filter_algos = [
    # 'buy_and_hodl.py',
    'buy_btc_simple.py',
    'buy_low_sell_high.py',
    # 'mean_reversion_simple.py',
    # 'rsi_profit_target.py',
    # 'simple_loop.py',
    # 'simple_universe.py',
]


class TestSuiteAlgo(WithLogger, CatalystTestCase):
    @staticmethod
    def analyze(context, perf):
        set_print_settings()

        transaction_df = extract_transactions(perf)
        print('the transactions:\n{}'.format(transaction_df))

        orders_df = extract_orders(perf)
        print('the orders:\n{}'.format(orders_df))

        stats = get_pretty_stats(perf, show_tail=False, num_rows=5)
        print('the stats:\n{}'.format(stats))
        pass

    def test_run_examples(self):
        # folder = join('..', '..', '..', 'catalyst', 'examples')
        HERE = os.path.dirname(os.path.abspath(__file__))
        folder = os.path.join(HERE, '..', '..', '..', 'catalyst', 'examples')

        files = [f for f in os.listdir(folder)
                 if os.path.isfile(os.path.join(folder, f))]

        algo_list = []
        for filename in files:
            name = os.path.basename(filename)
            if filter_algos and name not in filter_algos:
                continue

            module_name = 'catalyst.examples.{}'.format(
                name.replace('.py', '')
            )
            algo_list.append(module_name)

        exchanges = ['poloniex', 'bittrex', 'binance']
        asset_name = 'btc_usdt'
        quote_currency = 'usdt'
        capital_base = 10000
        data_freq = 'daily'
        start_date = pd.to_datetime('2017-10-01', utc=True)
        end_date = pd.to_datetime('2017-12-01', utc=True)

        for exchange_name in exchanges:
            ingest_exchange_bundles(exchange_name, data_freq, asset_name)

            for module_name in algo_list:
                algo = importlib.import_module(module_name)
                # namespace = module_name.replace('.', '_')

                log_catcher = TestHandler()
                with log_catcher:
                    run_algorithm(
                        capital_base=capital_base,
                        data_frequency=data_freq,
                        initialize=algo.initialize,
                        handle_data=algo.handle_data,
                        analyze=TestSuiteAlgo.analyze,
                        exchange_name=exchange_name,
                        algo_namespace='test_{}'.format(exchange_name),
                        quote_currency=quote_currency,
                        start=start_date,
                        end=end_date,
                        # output=out
                    )
                    warnings = [record for record in log_catcher.records if
                                record.level == WARNING]

                    assert(len(warnings) == 1)
                    assert (warnings[0].message == ALPHA_WARNING_MESSAGE)
                    assert (not log_catcher.has_errors)
                    assert (not log_catcher.has_criticals)

            clean_exchange_bundles(exchange_name, data_freq)
