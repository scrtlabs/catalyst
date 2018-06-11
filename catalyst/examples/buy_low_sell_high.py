import talib
import pandas as pd
from logbook import Logger

from catalyst.api import (
    order,
    order_target_percent,
    symbol,
    record,
)
from catalyst.exchange.utils.stats_utils import get_pretty_stats
from catalyst.utils.run_algo import run_algorithm

algo_namespace = 'buy_the_dip_live'
log = Logger('buy low sell high')


def initialize(context):
    log.info('initializing algo')
    context.ASSET_NAME = 'btc_usdt'
    context.asset = symbol(context.ASSET_NAME)

    context.TARGET_POSITIONS = 30
    context.PROFIT_TARGET = 0.1
    context.SLIPPAGE_ALLOWED = 0.02

    context.errors = []
    pass


def _handle_data(context, data):
    price = data.current(context.asset, 'price')
    log.info('got price {price}'.format(price=price))

    prices = data.history(
        context.asset,
        fields='price',
        bar_count=20,
        frequency='1D'
    )
    rsi = talib.RSI(prices.values, timeperiod=14)[-1]
    log.info('got rsi: {}'.format(rsi))

    # Buying more when RSI is low, this should lower our cost basis
    if rsi <= 30:
        buy_increment = 1
    elif rsi <= 40:
        buy_increment = 0.5
    elif rsi <= 70:
        buy_increment = 0.2
    else:
        buy_increment = 0.1

    cash = context.portfolio.cash
    log.info('base currency available: {cash}'.format(cash=cash))

    record(
        price=price,
        rsi=rsi,
    )

    orders = context.blotter.open_orders
    if orders:
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
        elif (position.amount > 0
              and price > cost_basis * (1 + context.PROFIT_TARGET)):
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
            log.info('the rsi is too high to consider buying {}'.format(rsi))
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
        order(
            asset=context.asset,
            amount=buy_increment,
            limit_price=price * (1 + context.SLIPPAGE_ALLOWED)
        )


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


if __name__ == '__main__':
    live = True
    if live:
        run_algorithm(
            capital_base=1000,
            initialize=initialize,
            handle_data=handle_data,
            analyze=analyze,
            exchange_name='bittrex',
            live=True,
            algo_namespace=algo_namespace,
            quote_currency='btc',
            simulate_orders=True,
        )
    else:
        run_algorithm(
            capital_base=10000,
            data_frequency='daily',
            initialize=initialize,
            handle_data=handle_data,
            analyze=analyze,
            exchange_name='poloniex',
            algo_namespace='buy_and_hodl',
            quote_currency='usdt',
            start=pd.to_datetime('2015-03-01', utc=True),
            end=pd.to_datetime('2017-10-31', utc=True),
        )
