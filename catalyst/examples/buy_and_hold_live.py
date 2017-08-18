from catalyst.utils.run_algo import run_algorithm
from datetime import datetime
import pytz
from logbook import Logger

from catalyst.api import (
    order,
    order_target_value,
    order_target_percent,
    symbol,
    record,
    cancel_order,
    get_open_orders,
)

log = Logger('buy_and_hold_live')


def initialize(context):
    log.info('initializing algo')
    context.asset = symbol('eos_usd')

    context.TARGET_HODL_RATIO = 0.8
    context.RESERVE_RATIO = 1.0 - context.TARGET_HODL_RATIO

    context.is_buying = True


def handle_data(context, data):
    log.info('handling bar {data}'.format(data=data))

    starting_cash = context.portfolio.starting_cash
    target_hodl_value = context.TARGET_HODL_RATIO * starting_cash
    reserve_value = context.RESERVE_RATIO * starting_cash
    log.info('starting cash: {}'.format(starting_cash))

    price = data.current(context.asset, 'price')
    log.info('got price {}'.format(price))

    # Stop buying after passing the reserve threshold
    # orders = get_open_orders(context.asset) or []
    # for order in orders:
    #     log.info('cancelling open order {}'.format(order))
    #     cancel_order(order)

    # Stop buying after passing the reserve threshold
    cash = context.portfolio.cash
    if cash <= reserve_value:
        context.is_buying = False

    log.info('cash {}'.format(cash))

    # Check if still buying and could (approximately) afford another purchase
    if context.is_buying and cash > price:
        # Place order to make position in asset equal to target_hodl_value
        order(context.asset, 1, limit_price=price + 1.1)
        # This works
        # order_target_value(
        #     context.asset,
        #     target_hodl_value,
        #     limit_price=price * 1.1,
        # )
        # order_target_percent(
        #     context.asset,
        #     0.01,
        #     limit_price=price * 1.1
        # )

    record(
        price=price,
        cash=cash,
        starting_cash=context.portfolio.starting_cash,
        leverage=context.account.leverage,
    )
    pass


exchange_conn = dict(
    name='bitfinex',
    key='',
    secret=b'',
    base_currency='usd'
)
run_algorithm(
    initialize=initialize,
    handle_data=handle_data,
    capital_base=100000,
    exchange_conn=exchange_conn,
    live=True,
    algo_namespace='buy_and_hold_live'
)
