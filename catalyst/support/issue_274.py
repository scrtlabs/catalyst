import pytz
from datetime import datetime, timedelta
from catalyst.api import symbol
from catalyst.utils.run_algo import run_algorithm
#from utils.data import load_coin_data_from_csv

exchange_name = 'bitfinex'
coin = 'btc'
base_currency = 'usd'
n_candles = 5
resample_frequency_minutes = 5


def initialize(context):
    context.symbol = symbol('%s_%s' % (coin, base_currency))
    # very simple method that reads data from generated csv file
    #context.all_data = load_coin_data_from_csv('btc', exchange_name, 'minute',
    #                                           from_date=datetime(2017, 6, 1, 0, 0, 0, 0, pytz.utc),
    #                                           resample='%dT' % resample_frequency_minutes)


def handle_data_polo_partial_candles(context, data):
    # all I do is print the current last 2 candles (5T)
    history = data.history(symbol('btc_usdt'), ['volume'], bar_count=10, frequency='1D')
    print('\nnow: %s\n%s' % (data.current_dt, history))
    if not hasattr(context, 'i'): context.i = 0
    context.i += 1
    if context.i > 5: raise Exception('stop')


run_algorithm(initialize=lambda ctx: True,
              handle_data=handle_data_polo_partial_candles,
              exchange_name='poloniex',
              base_currency='usdt',
              algo_namespace='ns',
              live=False,
              data_frequency='minute',
              capital_base=3000,
              start=datetime(2018, 2, 2, 0, 0, 0, 0, pytz.utc),
              end=datetime(2018, 2, 20, 0, 0, 0, 0, pytz.utc))


"""
def handle_data(context, data):
    #bundle_data = \
    #context.all_data[data.current_dt - timedelta(minutes=(n_candles - 1) * resample_frequency_minutes):][:n_candles][
    #    'close']
    backtest_data = data.history(context.symbol, 'close', bar_count=n_candles,
                                 frequency='%dT' % resample_frequency_minutes)
    print('current_time:', data.current_dt)

    #print('bundle_data:')
    #print(bundle_data)

    print('backtest_data:')
    print(backtest_data)
    #raise Exception('fail')


run_algorithm(
    initialize=initialize,
    handle_data=handle_data,
    exchange_name=exchange_name,
    base_currency=base_currency,
    algo_namespace='investigate_mismatching_final_candle',
    live=False,
    data_frequency='minute',
    capital_base=3000,
    simulate_orders=True,
    start=datetime(2018, 2, 2, 0, 0, 0, 0, pytz.utc),
    end=datetime(2018, 2, 3, 0, 0, 0, 0, pytz.utc))
"""