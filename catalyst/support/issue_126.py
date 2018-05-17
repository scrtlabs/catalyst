from catalyst import run_algorithm
from catalyst.api import order, record, symbol
import pandas as pd

from catalyst.exchange.utils.stats_utils import get_pretty_stats


def initialize(context):
    context.assets = [symbol('eth_btc'), symbol('eth_usdt')]


def handle_data(context, data):
    order(context.assets[0], 1)

    prices = data.current(context.assets, 'price')
    record(price=prices)
    pass


def analyze(context, perf):
    stats = get_pretty_stats(perf)
    print(stats)
    pass


if __name__ == '__main__':
    live = True
    if live:
        run_algorithm(
            capital_base=0.01,
            initialize=initialize,
            handle_data=handle_data,
            exchange_name='poloniex',
            algo_namespace='buy_btc_polo_jh',
            quote_currency='btc',
            analyze=analyze,
            live=True,
            simulate_orders=True,
        )
    else:
        run_algorithm(
            capital_base=1000,
            data_frequency='daily',
            initialize=initialize,
            handle_data=handle_data,
            exchange_name='poloniex',
            algo_namespace='buy_btc_polo_jh',
            quote_currency='usd',
            analyze=analyze,
            start=pd.to_datetime('2017-01-01', utc=True),
            end=pd.to_datetime('2017-12-25', utc=True),
        )
