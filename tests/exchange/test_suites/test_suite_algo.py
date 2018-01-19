import importlib
from os.path import join, isfile

import pandas as pd
import os

from catalyst import run_algorithm
from catalyst.exchange.utils.stats_utils import get_pretty_stats, \
    extract_transactions, set_print_settings, extract_orders
from catalyst.testing.fixtures import WithLogger, ZiplineTestCase
from logbook import TestHandler, WARNING
from pathtools.path import listdir

filter_algos = [
    'buy_and_hodl.py',
    'buy_btc_simple.py',
    'buy_low_sell_high.py',
    'mean_reversion_simple.py',
    'rsi_profit_target.py',
    'simple_loop.py',
    'simple_universe.py',
]


class TestSuiteAlgo(WithLogger, ZiplineTestCase):
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
        folder = join('..', '..', '..', 'catalyst', 'examples')
        files = [f for f in listdir(folder) if isfile(join(folder, f))]

        algo_list = []
        for filename in files:
            name = os.path.basename(filename)
            if filter_algos and name not in filter_algos:
                continue

            module_name = 'catalyst.examples.{}'.format(
                name.replace('.py', '')
            )
            algo_list.append(module_name)

        for module_name in algo_list:
            algo = importlib.import_module(module_name)
            namespace = module_name.replace('.', '_')

            log_catcher = TestHandler()
            with log_catcher:
                run_algorithm(
                    capital_base=0.1,
                    data_frequency='minute',
                    initialize=algo.initialize,
                    handle_data=algo.handle_data,
                    analyze=TestSuiteAlgo.analyze,
                    exchange_name='poloniex',
                    algo_namespace='test_{}'.format(namespace),
                    base_currency='eth',
                    start=pd.to_datetime('2017-10-01', utc=True),
                    end=pd.to_datetime('2017-10-02', utc=True),
                    # output=out
                )
                warnings = [record for record in log_catcher.records if
                            record.level == WARNING]

                if len(warnings) > 0:
                    print('WARNINGS:\n{}'.format(warnings))
            pass
