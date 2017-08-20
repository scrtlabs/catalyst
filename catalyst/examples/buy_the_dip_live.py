from logbook import Logger
from catalyst.utils.run_algo import run_algorithm
from catalyst.api import (
    order,
    order_target_percent,
    symbol,
    record,
    get_open_orders,
)
from catalyst.exchange.exchange_errors import ExchangeRequestError
import matplotlib.pyplot as plt

algo_namespace = 'buy_the_dip_live'
log = Logger(algo_namespace)


def initialize(context):
    log.info('initializing algo')
    context.ASSET_NAME = 'EOS_USD'
    context.TICK_SIZE = 1000.0
    context.asset = symbol(context.ASSET_NAME)

    context.TARGET_POSITIONS = 100
    context.BUY_INCREMENT = 1

    context.retry_check_open_orders = 2
    context.retry_update_portfolio = 2
    context.retry_order = 2


def handle_data(context, data):
    log.info('handling bar {data}'.format(data=data))
    # price_history = data.history(symbol('iot_usd'),
    #                     fields='price',
    #                     bar_count=20,
    #                     frequency='1d'
    #                     )
    # ohlc = data.history([context.asset, symbol('iot_usd')],
    #                     fields='price',
    #                     bar_count=20,
    #                     frequency='1d'
    #                     )
    ohlc = data.history(context.asset,
                        fields=['price', 'volume'],
                        bar_count=120,
                        frequency='1m'
                        )
    # ohlc = data.history([context.asset, symbol('iot_usd')],
    #                     fields=['price', 'volume'],
    #                     bar_count=20,
    #                     frequency='1d'
    #                     )

    hist_price = ohlc['price']

    cash = context.portfolio.cash
    log.info('base currency available: {cash}'.format(cash=cash))

    price = data.current(context.asset, 'price')
    log.info('got price {price}'.format(price=price))

    orders = get_open_orders(context.asset)
    if orders:
        log.info('skipping bar until all open orders execute')
        return

    if price * context.BUY_INCREMENT > cash:
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
        elif price > cost_basis * 1.1:
            log.info('price higher than cost basis, taking profit')
            order_target_percent(
                asset=context.asset,
                target=0,
                limit_price=price * 0.95,
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
            amount=context.BUY_INCREMENT,
            limit_price=price * 1.1
        )

    record(
        price=price,
        cash=cash,
        starting_cash=context.portfolio.starting_cash,
        leverage=context.account.leverage,
    )

    pass


def analyze(context, stats):
    pnl, = plt.plot(stats.index, stats['pnl'], '-',
                         color='blue',
                         linewidth=1.0,
                         label='P&L',
                         )

    plt.legend(handles=[pnl])
    plt.show()
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
