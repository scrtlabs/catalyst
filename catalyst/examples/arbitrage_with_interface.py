import talib
from logbook import Logger

from catalyst.api import (
    order,
    order_target_percent,
    symbol,
    record,
    get_open_orders,
)
from catalyst.exchange.stats_utils import get_pretty_stats
from catalyst.utils.run_algo import run_algorithm

algo_namespace = 'arbitrage_neo_eth'
log = Logger(algo_namespace)


def initialize(context):
    log.info('initializing arbitrage algorithm')

    context.buying_exchange = 'bittrex'
    context.selling_exchange = 'bitfinex'

    context.trading_pair_symbol = 'neo_eth'
    context.trading_pairs = dict()
    context.trading_pairs[context.buying_exchange] = \
        symbol(context.trading_pair_symbol, context.buying_exchange)
    context.trading_pairs[context.selling_exchange] = \
        symbol(context.trading_pair_symbol, context.selling_exchange)

    context.entry_points = [
        dict(gap=0.001, amount=0.05),
        dict(gap=0.002, amount=0.1),
    ]
    context.exit_points = [
        dict(gap=0, amount=0.05),
        dict(gap=-0.001, amount=0.01),
    ]

    context.MAX_POSITIONS = 50
    context.SLIPPAGE_ALLOWED = 0.02

    pass


def place_order(context, amount, buying_price, selling_price,
                action):
    if action == 'enter':
        buying_exchange = context.exchanges[context.buying_exchange]
        buy_price = buying_price

        selling_exchange = context.exchanges[context.selling_exchange]
        sell_price = selling_price

    elif action == 'exit':
        buying_exchange = context.exchanges[context.selling_exchange]
        buy_price = selling_price

        selling_exchange = context.exchanges[context.buying_exchange]
        sell_price = buying_price

    else:
        raise ValueError('invalid order action')

    base_currency = buying_exchange.base_currency
    base_currency_amount = buying_exchange.portfolio.cash

    sell_balances = selling_exchange.get_balances()
    sell_currency = context.trading_pairs[
        context.selling_exchange].market_currency

    if sell_currency in sell_balances:
        market_currency_amount = sell_balances[sell_currency]
    else:
        log.warn('the selling exchange {} does not hold currency {}'.format(
            selling_exchange.name, sell_currency
        ))
        return

    if base_currency_amount < amount:
        log.warn('not enough {} ({}) to buy {}, adjusting the amount'.format(
            base_currency, base_currency_amount, amount))
        amount = base_currency_amount
    elif market_currency_amount < amount:
        log.warn('not enough {} ({}) to sell {}, aborting'.format(
            sell_currency, market_currency_amount, amount))
        return

    adj_buy_price = buy_price * (1 + context.SLIPPAGE_ALLOWED)
    log.info('buying {} limit at {}{} on {}'.format(
        amount, buying_price, context.trading_pair_symbol,
        buying_exchange.name))
    order(
        asset=context.trading_pairs[buying_exchange],
        amount=amount,
        limit_price=adj_buy_price
    )

    adj_sell_price = sell_price * (1 - context.SLIPPAGE_ALLOWED)
    log.info('selling {} limit at {}{} on {}'.format(
        amount, adj_sell_price, context.trading_pair_symbol,
        selling_exchange.name))
    order(
        asset=context.trading_pairs[selling_exchange],
        amount=amount,
        limit_price=adj_sell_price
    )
    pass


def handle_data(context, data):
    log.info('handling bar {}'.format(data.current_dt))

    buying_price = data.current(
        context.trading_pairs[context.buying_exchange], 'price')
    log.info('price on buying exchange {exchange}: {price}'.format(
        exchange=context.buying_exchange.upper(),
        price=buying_price,
    ))

    selling_price = data.current(
        context.trading_pairs[context.selling_exchange], 'price')

    log.info('price on selling exchange {exchange}: {price}'.format(
        exchange=context.selling_exchange.upper(),
        price=selling_price,
    ))

    # If for example,
    #   selling price = 50
    #   buying price = 25
    #   expected gap = 1

    # If follows that,
    #   selling price - buying price / buying price
    #   50 - 25 / 25 = 1
    gap = (selling_price - buying_price) / buying_price
    log.info('the price gap: {} ({}%)'.format(gap, gap * 100))

    # Consider the least ambitious entry point first
    # Override of wider gap is found
    entry_points = sorted(
        context.entry_points,
        key=lambda point: point['gap'],
    )

    buy_amount = None
    for entry_point in entry_points:
        if gap > entry_point['gap']:
            buy_amount = entry_point['amount']

    if buy_amount:
        log.info('found buy trigger for amount: {}'.format(buy_amount))
        place_order(context, buy_amount, buying_price, selling_price, 'enter')

    else:
        # Consider the narrowest exit gap first
        # Override of wider gap is found
        exit_points = sorted(
            context.exit_points,
            key=lambda point: point['gap'],
            reverse=True
        )

        sell_amount = None
        for exit_point in exit_points:
            if gap < exit_point['gap']:
                sell_amount = exit_point['amount']

        if sell_amount:
            log.info('found sell trigger for amount: {}'.format(sell_amount))
            place_order(context, sell_amount, buying_price, selling_price,
                        'exit')


def analyze(context, stats):
    log.info('the daily stats:\n{}'.format(get_pretty_stats(stats)))
    pass


run_algorithm(
    initialize=initialize,
    handle_data=handle_data,
    analyze=analyze,
    exchange_name='bittrex,bitfinex',
    live=True,
    algo_namespace=algo_namespace,
    base_currency='eth',
    live_graph=False
)
