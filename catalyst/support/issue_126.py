from catalyst import run_algorithm
from catalyst.api import order, record, symbol
import pandas as pd


def initialize(context):
    context.asset = symbol('btc_usdt')


def handle_data(context, data):
    order(context.asset, 1)

    price = data.current(context.asset, 'price')
    record(btc=price)
    pass


def analyze(context, perf):
    pass


if __name__ == '__main__':
    run_algorithm(
        capital_base=1000,
        data_frequency='daily',
        initialize=initialize,
        handle_data=handle_data,
        exchange_name='poloniex',
        algo_namespace='buy_btc_polo_jh',
        base_currency='usd',
        analyze=analyze,
        start=pd.to_datetime('2017-01-01', utc=True),
        end=pd.to_datetime('2017-12-25', utc=True),
    )
