from catalyst.api import symbol
from catalyst.utils.run_algo import run_algorithm


def initialize(context):
    pass


def handle_data(context, data):
    data.history(symbol("DASH_BTC"), ['close'],
                 bar_count=200, frequency='15T')


run_algorithm(initialize=lambda ctx: True,
              handle_data=handle_data,
              exchange_name='poloniex',
              quote_currency='usd',
              algo_namespace='issue-420',
              live=True,
              data_frequency='daily',
              capital_base=3000)
