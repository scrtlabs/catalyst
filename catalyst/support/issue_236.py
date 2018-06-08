from catalyst.api import symbol
from catalyst.utils.run_algo import run_algorithm

coins = ['dash', 'btc', 'dash', 'etc', 'eth', 'ltc', 'nxt', 'rep', 'str', 'xmr', 'xrp', 'zec']
symbols = None


def initialize(context):
    pass


def _handle_data(context, data):
    global symbols
    if symbols is None: symbols = [symbol(c + '_usdt') for c in coins]

    print'getting history for: %s' % [s.symbol for s in symbols]
    history = data.history(symbols,
                    ['close', 'volume'],
                    bar_count=1, # EXCEPTION, Change to 2
                    frequency='5T')
    #print 'history: %s' % history.shape

run_algorithm(initialize=initialize,
              handle_data=_handle_data,
              analyze=lambda _, results: True,
              exchange_name='poloniex',
              quote_currency='usdt',
              algo_namespace='issue-236',
              live=True,
              data_frequency='minute',
              capital_base=3000,
              simulate_orders=True)