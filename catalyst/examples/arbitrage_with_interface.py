from logbook import Logger

from catalyst.api import (
    record,
    order,
    symbol,
    get_open_orders
)
from catalyst.exchange.utils.stats_utils import get_pretty_stats
from catalyst.utils.run_algo import run_algorithm

algo_namespace = 'arbitrage_eth_btc'
log = Logger(algo_namespace)


def initialize(context):
    log.info('initializing arbitrage algorithm')

    # The context contains a new "exchanges" attribute which is a dictionary
    # of exchange objects by exchange name. This allow easy access to the
    # exchanges.
    context.buying_exchange = context.exchanges['poloniex']
    context.selling_exchange = context.exchanges['bitfinex']

    context.trading_pair_symbol = 'eth_btc'
    context.trading_pairs = dict()

    # Note the second parameter of the symbol() method
    # Passing the exchange name here returns a TradingPair object including
    # the exchange information. This allow all other operations using
    # the TradingPair to target the correct exchange.
    context.trading_pairs[context.buying_exchange] = \
        symbol('eth_btc', context.buying_exchange.name)

    context.trading_pairs[context.selling_exchange] = \
        symbol(context.trading_pair_symbol, context.selling_exchange.name)

    context.entry_points = [
        dict(gap=0.03, amount=0.05),
        dict(gap=0.04, amount=0.1),
        dict(gap=0.05, amount=0.5),
    ]
    context.exit_points = [
        dict(gap=-0.02, amount=0.5),
    ]

    context.SLIPPAGE_ALLOWED = 0.02
    pass


def place_orders(context, amount, buying_price, selling_price, action):
    """
    This method will always place two orders of the same amount to keep
    the currency position the same as it moves between the two exchanges.

    :param context: TradingAlgorithm
    :param amount: float
        The trading pair amount to trade on both exchanges.
    :param buying_price: float
        The current trading pair price on the buying exchange.
    :param selling_price: float
        The current trading pair price on the selling exchange.
    :param action: string
        "enter": buys on the buying exchange and sells on the selling exchange
        "exit": buys on the selling exchange and sells on the buying exchange

    :return:
    """
    if action == 'enter':
        enter_exchange = context.buying_exchange
        entry_price = buying_price

        exit_exchange = context.selling_exchange
        exit_price = selling_price

    elif action == 'exit':
        enter_exchange = context.selling_exchange
        entry_price = selling_price

        exit_exchange = context.buying_exchange
        exit_price = buying_price

    else:
        raise ValueError('invalid order action')

    quote_currency = enter_exchange.quote_currency
    quote_currency_amount = enter_exchange.portfolio.cash

    exit_balances = exit_exchange.get_balances()
    exit_currency = context.trading_pairs[
        context.selling_exchange].quote_currency

    if exit_currency in exit_balances:
        quote_currency_amount = exit_balances[exit_currency]
    else:
        log.warn(
            'the selling exchange {exchange_name} does not hold '
            'currency {currency}'.format(
                exchange_name=exit_exchange.name,
                currency=exit_currency
            )
        )
        return

    if quote_currency_amount < (amount * entry_price):
        adj_amount = quote_currency_amount / entry_price
        log.warn(
            'not enough {quote_currency} ({quote_currency_amount}) to buy '
            '{amount}, adjusting the amount to {adj_amount}'.format(
                quote_currency=quote_currency,
                quote_currency_amount=quote_currency_amount,
                amount=amount,
                adj_amount=adj_amount
            )
        )
        amount = adj_amount

    elif quote_currency_amount < amount:
        log.warn(
            'not enough {currency} ({currency_amount}) to sell '
            '{amount}, aborting'.format(
                currency=exit_currency,
                currency_amount=quote_currency_amount,
                amount=amount
            )
        )
        return

    adj_buy_price = entry_price * (1 + context.SLIPPAGE_ALLOWED)
    log.info(
        'buying {amount} {trading_pair} on {exchange_name} with price '
        'limit {limit_price}'.format(
            amount=amount,
            trading_pair=context.trading_pair_symbol,
            exchange_name=enter_exchange.name,
            limit_price=adj_buy_price
        )
    )
    order(
        asset=context.trading_pairs[enter_exchange],
        amount=amount,
        limit_price=adj_buy_price
    )

    adj_sell_price = exit_price * (1 - context.SLIPPAGE_ALLOWED)
    log.info(
        'selling {amount} {trading_pair} on {exchange_name} with price '
        'limit {limit_price}'.format(
            amount=-amount,
            trading_pair=context.trading_pair_symbol,
            exchange_name=exit_exchange.name,
            limit_price=adj_sell_price
        )
    )
    order(
        asset=context.trading_pairs[exit_exchange],
        amount=-amount,
        limit_price=adj_sell_price
    )
    pass


def handle_data(context, data):
    log.info('handling bar {}'.format(data.current_dt))

    buying_price = data.current(
        context.trading_pairs[context.buying_exchange], 'price')

    log.info('price on buying exchange {exchange}: {price}'.format(
        exchange=context.buying_exchange.name.upper(),
        price=buying_price,
    ))

    selling_price = data.current(
        context.trading_pairs[context.selling_exchange], 'price')

    log.info('price on selling exchange {exchange}: {price}'.format(
        exchange=context.selling_exchange.name.upper(),
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
    log.info(
        'the price gap: {gap} ({gap_percent}%)'.format(
            gap=gap,
            gap_percent=gap * 100
        )
    )
    record(buying_price=buying_price, selling_price=selling_price, gap=gap)

    # Waiting for orders to close before initiating new ones
    for exchange in context.trading_pairs:
        asset = context.trading_pairs[exchange]

        orders = get_open_orders(asset)
        if orders:
            log.info(
                'found {order_count} open orders on {exchange_name} '
                'skipping bar until all open orders execute'.format(
                    order_count=len(orders),
                    exchange_name=exchange.name
                )
            )
            return

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
        place_orders(
            context=context,
            amount=buy_amount,
            buying_price=buying_price,
            selling_price=selling_price,
            action='enter'
        )

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
            place_orders(
                context=context,
                amount=sell_amount,
                buying_price=buying_price,
                selling_price=selling_price,
                action='exit'
            )


def analyze(context, stats):
    log.info('the daily stats:\n{}'.format(get_pretty_stats(stats)))
    pass


if __name__ == '__main__':
    # The execution mode: backtest or live
    MODE = 'live'
    if MODE == 'live':
        run_algorithm(
            capital_base=0.1,
            initialize=initialize,
            handle_data=handle_data,
            analyze=analyze,
            exchange_name='poloniex,bitfinex',
            live=True,
            algo_namespace=algo_namespace,
            quote_currency='btc',
            live_graph=False,
            simulate_orders=True,
            stats_output=None,
        )
