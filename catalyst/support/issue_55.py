import pandas as pd

from catalyst import run_algorithm
from catalyst.api import symbol


def initialize(context):
    print('initializing')
    context.asset = symbol('xcp_btc')


def handle_data(context, data):
    print('handling bar: {}'.format(data.current_dt))

    price = data.current(context.asset, 'close')
    print('got price {price}'.format(price=price))

    try:
        prices = data.history(
            context.asset,
            fields='close',
            bar_count=1,
            frequency='1D'
        )
        print('got {} price entries\n'.format(len(prices), prices))
    except Exception as e:
        print(e)


run_algorithm(
    capital_base=1,
    start=pd.to_datetime('2015-3-2', utc=True),
    end=pd.to_datetime('2017-8-31', utc=True),
    data_frequency='daily',
    initialize=initialize,
    handle_data=handle_data,
    analyze=None,
    exchange_name='poloniex',
    algo_namespace='issue_55',
    quote_currency='btc'
)
