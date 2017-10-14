import pandas as pd

from catalyst import run_algorithm
from catalyst.api import symbol


def initialize(context):
    print('initializing')
    context.asset = symbol('gno_btc')


def handle_data(context, data):
    print('handling bar: {}'.format(data.current_dt))

    price = data.current(context.asset, 'close')
    print('got price {price}'.format(price=price))


run_algorithm(
    capital_base=250,
    start=pd.to_datetime('2017-5-1', utc=True),
    end=pd.to_datetime('2017-5-31', utc=True),
    data_frequency='minute',
    initialize=initialize,
    handle_data=handle_data,
    analyze=None,
    exchange_name='poloniex',
    algo_namespace='simple_loop',
    base_currency='btc'
)
