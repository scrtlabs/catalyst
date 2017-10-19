import pandas as pd
import talib

from catalyst import run_algorithm
from catalyst.api import symbol


def initialize(context):
    print('initializing')
    context.asset = symbol('btc_usdt')


def handle_data(context, data):
    print('handling bar: {}'.format(data.current_dt))

    price = data.current(context.asset, 'close')
    print('got price {price}'.format(price=price))

    prices = data.history(
        context.asset,
        fields='price',
        bar_count=15,
        frequency='1d'
    )
    rsi = talib.RSI(prices.values, timeperiod=14)[-1]
    print('got rsi: {}'.format(rsi))
    pass


run_algorithm(
    capital_base=250,
    start=pd.to_datetime('2015-2-19', utc=True),
    end=pd.to_datetime('2017-9-30', utc=True),
    data_frequency='daily',
    initialize=initialize,
    handle_data=handle_data,
    analyze=None,
    exchange_name='poloniex',
    algo_namespace='simple_loop',
    base_currency='eth'
)
