import talib
from logbook import Logger
import pandas as pd

from catalyst.api import (
    order,
    order_target_percent,
    symbol,
    record,
    get_open_orders,
)
from catalyst.exchange.stats_utils import get_pretty_stats
from catalyst.utils.run_algo import run_algorithm

algo_namespace = 'buy_low_sell_high_neo'
log = Logger(algo_namespace)


def initialize(context):
    log.info('initializing algo')
    context.asset = symbol('neo_btc', 'bitfinex')

    context.TARGET_POSITIONS = 50000
    context.PROFIT_TARGET = 0.1
    context.SLIPPAGE_ALLOWED = 0.02

    context.retry_check_open_orders = 10
    context.retry_update_portfolio = 10
    context.retry_order = 5

    context.errors = []
    pass


def _handle_data(context, data):
    prices = data.history(
        context.asset,
        fields='price',
        bar_count=30,
        frequency='30m'
    )
    rsi = talib.RSI(prices.values, timeperiod=14)[-1]
    log.info('got rsi: {}'.format(rsi))

    # Buying more when RSI is low, this should lower our cost basis
    if rsi <= 30:
        buy_increment = 1
    elif rsi <= 40:
        buy_increment = 0.5
    elif rsi <= 70:
        buy_increment = 0.1
    else:
        buy_increment = None

    cash = context.portfolio.cash
    log.info('base currency available: {cash}'.format(cash=cash))

    price = data.current(context.asset, 'close')
    log.info('got price {price}'.format(price=price))

    if price is None:
        log.warn('no pricing data')
        return

    record(price=price)

    orders = get_open_orders(context.asset)
    if len(orders) > 0:
        log.info('skipping bar until all open orders execute')
        return

    is_buy = False
    cost_basis = None
    if context.asset in context.portfolio.positions:
        position = context.portfolio.positions[context.asset]

        cost_basis = position.cost_basis
        log.info(
            'found {amount} positions with cost basis {cost_basis}'.format(
                amount=position.amount,
                cost_basis=cost_basis
            )
        )

        if position.amount >= context.TARGET_POSITIONS:
            log.info('reached positions target: {}'.format(position.amount))
            return

        if price < cost_basis:
            is_buy = True
        elif position.amount > 0 and \
                        price > cost_basis * (1 + context.PROFIT_TARGET):
            profit = (price * position.amount) - (cost_basis * position.amount)
            log.info('closing position, taking profit: {}'.format(profit))
            order_target_percent(
                asset=context.asset,
                target=0,
                limit_price=price * (1 - context.SLIPPAGE_ALLOWED),
            )
        else:
            log.info('no buy or sell opportunity found')
    else:
        is_buy = True

    if is_buy:
        if buy_increment is None:
            return

        if price * buy_increment > cash:
            log.info('not enough base currency to consider buying')
            return

        log.info(
            'buying position cheaper than cost basis {} < {}'.format(
                price,
                cost_basis
            )
        )
        limit_price = price * (1 + context.SLIPPAGE_ALLOWED)
        order(
            asset=context.asset,
            amount=buy_increment,
            limit_price=limit_price
        )
        pass


def handle_data(context, data):
    log.info('handling bar {}'.format(data.current_dt))
    # try:
    _handle_data(context, data)
    # except Exception as e:
    #     log.warn('aborting the bar on error {}'.format(e))
    #     context.errors.append(e)

    log.info('completed bar {}, total execution errors {}'.format(
        data.current_dt,
        len(context.errors)
    ))

    if len(context.errors) > 0:
        log.info('the errors:\n{}'.format(context.errors))


def analyze(context, stats):
    log.info('the daily stats:\n{}'.format(get_pretty_stats(stats)))
    pass


# run_algorithm(
#     initialize=initialize,
#     handle_data=handle_data,
#     analyze=analyze,
#     exchange_name='bittrex,bitfinex',
#     live=True,
#     algo_namespace=algo_namespace,
#     base_currency='eth',
#     live_graph=True
# )
run_algorithm(
    capital_base=250,
    start=pd.to_datetime('2017-09-08', utc=True),
    end=pd.to_datetime('2017-09-15', utc=True),
    data_frequency='minute',
    initialize=initialize,
    handle_data=handle_data,
    analyze=analyze,
    exchange_name='bitfinex',
    algo_namespace=algo_namespace,
    base_currency='btc'
)
