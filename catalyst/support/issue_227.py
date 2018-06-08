import pytz
from datetime import datetime
from catalyst.api import symbol
from catalyst.utils.run_algo import run_algorithm

coin = 'btc'
quote_currency = 'usd'
n_candles = 5


def initialize(context):
    context.symbol = symbol('%s_%s' % (coin, quote_currency))


def handle_data_polo_partial_candles(context, data):
    history = data.history(symbol('btc_usdt'), ['volume'],
                           bar_count=10,
                           frequency='4H')
    print('\nnow: %s\n%s' % (data.current_dt, history))
    if not hasattr(context, 'i'):
        context.i = 0
    context.i += 1
    if context.i > 5:
        raise Exception('stop')


live = False

if live:
    run_algorithm(initialize=lambda ctx: True,
                  handle_data=handle_data_polo_partial_candles,
                  exchange_name='poloniex',
                  quote_currency='usdt',
                  algo_namespace='ns',
                  live=True,
                  data_frequency='minute',
                  capital_base=3000)
else:
    run_algorithm(initialize=lambda ctx: True,
                  handle_data=handle_data_polo_partial_candles,
                  exchange_name='poloniex',
                  quote_currency='usdt',
                  algo_namespace='ns',
                  live=False,
                  data_frequency='minute',
                  capital_base=3000,
                  start=datetime(2018, 2, 2, 0, 0, 0, 0, pytz.utc),
                  end=datetime(2018, 2, 20, 0, 0, 0, 0, pytz.utc)
                  )
