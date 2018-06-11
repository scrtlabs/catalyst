from catalyst.api import symbol
from catalyst.utils.run_algo import run_algorithm

def initialize(context):
    pass


def handle_data(context, data):
    history = data.history(symbol('btc_usd'), ['volume'],
                           bar_count=288,
                           frequency='5T')

    print('\nnow: %s\n%s' % (data.current_dt, history))
    if not hasattr(context, 'i'):
        context.i = 0
    context.i += 1
    if context.i > 5:
        raise Exception('stop')


live = True
if live:
    run_algorithm(initialize=lambda ctx: True,
                  handle_data=handle_data,
                  exchange_name='gdax',
                  quote_currency='usd',
                  algo_namespace='issue-323',
                  live=True,
                  data_frequency='daily',
                  capital_base=3000,
                  )

