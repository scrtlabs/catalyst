from logbook import Logger

from catalyst import run_algorithm
from catalyst.api import order_target_percent

NAMESPACE = 'goose7'
log = Logger(NAMESPACE)

from catalyst.api import record, symbol


def initialize(context):
    context.asset = symbol('trx_btc')


def handle_data(context, data):
    price = data.current(context.asset, 'price')
    record(btc=price)

    # Only ordering if it does not have any position to avoid trying some
    # tiny orders with the leftover btc
    pos_amount = context.portfolio.positions[context.asset].amount
    if pos_amount > 0:
        return

    # Adding a limit price to workaround an issue with performance
    # calculations of market orders
    order_target_percent(
        context.asset, 1, limit_price=price * 1.01
    )


if __name__ == '__main__':
    run_algorithm(
        capital_base=0.003,
        initialize=initialize,
        handle_data=handle_data,
        exchange_name='binance',
        live=True,
        algo_namespace=NAMESPACE,
        quote_currency='btc',
        live_graph=False,
        simulate_orders=False,
    )
