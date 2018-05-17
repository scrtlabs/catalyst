import pandas as pd

from catalyst import run_algorithm
from catalyst.api import symbol


def initialize(context):
    context.asset = symbol('btc_usdt')


def handle_data(context, data):
    df = data.history(context.asset,
                      'close',
                      bar_count=10,
                      frequency='5T',
                      )


if __name__ == '__main__':
    LIVE = True
    if LIVE:
        run_algorithm(
            capital_base=1,
            initialize=initialize,
            handle_data=handle_data,
            exchange_name='poloniex',
            algo_namespace='test_algo',
            quote_currency='usdt',
            live=True,
            simulate_orders=True,
        )
    else:
        run_algorithm(
            capital_base=1,
            data_frequency='minute',
            initialize=initialize,
            handle_data=handle_data,
            exchange_name='poloniex',
            algo_namespace='test_algo',
            quote_currency='usdt',
            live=False,
            start=pd.to_datetime('2017-12-1', utc=True),
            end=pd.to_datetime('2017-12-1', utc=True),
        )
