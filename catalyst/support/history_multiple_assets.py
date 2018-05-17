import pandas as pd

from catalyst import run_algorithm
from catalyst.api import symbol


def initialize(context):
    context.asset1 = symbol('fct_btc')
    context.asset2 = symbol('btc_usdt')
    context.coins = [context.asset1, context.asset2]


def handle_data(context, data):
    df = data.history(context.coins,
                      'close',
                      bar_count=10,
                      frequency='5T',
                      )
    print(df)
    print(data.current(context.asset1, 'close'))
    print(data.current(context.asset2, 'close'))
    exit(0)


if __name__ == '__main__':
    LIVE = True
    if LIVE:
        run_algorithm(
            capital_base=1,
            initialize=initialize,
            handle_data=handle_data,
            exchange_name='poloniex',
            algo_namespace='test_multi_assets',
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
            algo_namespace='test_multi_assets',
            quote_currency='usdt',
            live=False,
            start=pd.to_datetime('2017-12-1', utc=True),
            end=pd.to_datetime('2017-12-1', utc=True),
        )
