from catalyst.api import symbol
from catalyst.utils.run_algo import run_algorithm


def initialize(context):
    context.asset = symbol('bcc_usdt')


def handle_data(context, data):
    data.history(context.asset, ['close'], bar_count=100, frequency='5T')


def analyze(context=None, results=None):
    pass


if __name__ == '__main__':
    run_algorithm(
        capital_base=100,
        initialize=initialize,
        handle_data=handle_data,
        analyze=analyze,
        exchange_name='bittrex',
        algo_namespace="bittrex_is_broken",
        quote_currency='usdt',
        data_frequency='minute',
        simulate_orders=True,
        live=True)
