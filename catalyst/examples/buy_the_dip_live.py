from logbook import Logger
from catalyst.utils.run_algo import run_algorithm
from catalyst.api import (
    order,
    order_target_percent,
    symbol,
    record,
    get_open_orders,
)
from catalyst.errors import ZiplineError
import talib

algo_namespace = 'buy_the_dip_live'
log = Logger(algo_namespace)


def initialize(context):
    log.info('initializing algo')
    context.ASSET_NAME = 'IOT_USD'
    context.asset = symbol(context.ASSET_NAME)

    context.TARGET_POSITIONS = 200
    context.PROFIT_TARGET = 0.1
    context.SLIPPAGE_ALLOWED = 0.02

    context.retry_check_open_orders = 2
    context.retry_update_portfolio = 2
    context.retry_order = 2

    context.errors = []


def _handle_data(context, data):
    prices = data.history(
        context.asset,
        fields='price',
        bar_count=20,
        frequency='15m'
    )
    rsi = talib.RSI(prices.values, timeperiod=14)[-1]
    log.info('got rsi: {}'.format(rsi))

    # Buying more when RSI is low, this should lower our cost basis
    if rsi <= 40:
        buy_increment = 2
    elif rsi <= 30:
        buy_increment = 5
    else:
        buy_increment = 1

    cash = context.portfolio.cash
    log.info('base currency available: {cash}'.format(cash=cash))

    price = data.current(context.asset, 'price')
    log.info('got price {price}'.format(price=price))

    orders = get_open_orders(context.asset)
    if orders:
        log.info('skipping bar until all open orders execute')
        return

    if price * buy_increment > cash:
        log.info('not enough base currency to consider buying')
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
        if price < cost_basis:
            is_buy = True
        elif price > cost_basis * (1 + context.PROFIT_TARGET) or rsi > 70:
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
        log.info(
            'buying position cheaper than cost basis {} < {}'.format(
                price,
                cost_basis
            )
        )
        order(
            asset=context.asset,
            amount=buy_increment,
            limit_price=price * (1 + context.SLIPPAGE_ALLOWED)
        )

    record(
        price=price,
        cash=cash,
        starting_cash=context.portfolio.starting_cash,
        leverage=context.account.leverage,
    )


def handle_data(context, data):
    log.info('handling bar {}'.format(data.current_dt))
    try:
        _handle_data(context, data)
    except ZiplineError as e:
        log.warn('aborting the bar on error {}'.format(e))
        context.errors.append(e)

    log.info('completed bar {}, total execution errors {}'.format(
        data.current_dt,
        len(context.errors)
    ))

    if len(context.errors) > 0:
        log.info('the errors:\n{}'.format(context.errors))


def analyze(context, stats):
    log.info('the full stats:\n{}'.format(stats))
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
    analyze=analyze,
    capital_base=100000,
    exchange_conn=exchange_conn,
    live=True,
    algo_namespace=algo_namespace
)
