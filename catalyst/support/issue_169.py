import pandas as pd
from catalyst.utils.run_algo import run_algorithm
from catalyst.api import symbol
from exchange.utils.stats_utils import set_print_settings


def initialize(context):
    context.i = 0
    context.data = []


def handle_data(context, data):
    prices = data.history(
        symbol('xlm_eth'),
        fields=['open', 'high', 'low', 'close'],
        bar_count=50,
        frequency='1T'
    )
    set_print_settings()
    print(prices.tail(10))
    context.data.append(prices)

    context.i = context.i + 1
    if context.i == 3:
        context.interrupt_algorithm()


def analyze(context, prefs):
    for dataset in context.data:
        print(dataset[-2:])


if __name__ == '__main__':
    run_algorithm(
        capital_base=0.1,
        initialize=initialize,
        handle_data=handle_data,
        analyze=analyze,
        exchange_name='binance',
        algo_namespace='Test candles',
        quote_currency='eth',
        data_frequency='minute',
        live=True,
        simulate_orders=True)
