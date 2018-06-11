from datetime import timedelta

import pandas as pd
import numpy as np
import talib
from logbook import Logger

from catalyst.api import (
    order,
    symbol,
    record,
    get_open_orders,
)
from catalyst.utils.run_algo import run_algorithm

algo_namespace = 'rsi'
log = Logger(algo_namespace)


def initialize(context):
    log.info('initializing algo')
    context.asset = symbol('eth_btc')
    context.base_price = None

    context.MAX_HOLDINGS = 0.2
    context.RSI_OVERSOLD = 30
    context.RSI_OVERSOLD_BBANDS = 45
    context.RSI_OVERBOUGHT_BBANDS = 55
    context.SLIPPAGE_ALLOWED = 0.03

    context.TARGET = 0.15
    context.STOP_LOSS = 0.1
    context.STOP = 0.03
    context.position = None

    context.last_bar = None

    context.errors = []
    pass


def _handle_buy_sell_decision(context, data, signal, price):
    orders = get_open_orders(context.asset)
    if len(orders) > 0:
        log.info('skipping bar until all open orders execute')
        return

    positions = context.portfolio.positions
    if context.position is None and context.asset in positions:
        position = positions[context.asset]
        context.position = dict(
            cost_basis=position['cost_basis'],
            amount=position['amount'],
            stop=None
        )

    # action = None
    if context.position is not None:
        cost_basis = context.position['cost_basis']
        amount = context.position['amount']
        log.info(
            'found {amount} positions with cost basis {cost_basis}'.format(
                amount=amount,
                cost_basis=cost_basis
            )
        )
        stop = context.position['stop']

        target = cost_basis * (1 + context.TARGET)
        if price >= target:
            context.position['cost_basis'] = price
            context.position['stop'] = context.STOP

        stop_target = context.STOP_LOSS if stop is None else context.STOP
        if price < cost_basis * (1 - stop_target):
            log.info('executing stop loss')
            order(
                asset=context.asset,
                amount=-amount,
                limit_price=price * (1 - context.SLIPPAGE_ALLOWED),
            )
            # action = 0
            context.position = None

    else:
        if signal == 'long':
            log.info('opening position')
            buy_amount = context.MAX_HOLDINGS / price
            order(
                asset=context.asset,
                amount=buy_amount,
                limit_price=price * (1 + context.SLIPPAGE_ALLOWED),
            )
            context.position = dict(
                cost_basis=price,
                amount=buy_amount,
                stop=None
            )
            # action = 0


def _handle_data_rsi_only(context, data):
    price = data.current(context.asset, 'close')
    log.info('got price {price}'.format(price=price))

    if price is np.nan:
        log.warn('no pricing data')
        return

    if context.base_price is None:
        context.base_price = price

    try:
        prices = data.history(
            context.asset,
            fields='price',
            bar_count=20,
            frequency='30T'
        )
    except Exception as e:
        log.warn('historical data not available: '.format(e))
        return

    rsi = talib.RSI(prices.values, timeperiod=16)[-1]
    log.info('got rsi {}'.format(rsi))

    signal = None
    if rsi < context.RSI_OVERSOLD:
        signal = 'long'

    # Making sure that the price is still current
    price = data.current(context.asset, 'close')
    cash = context.portfolio.cash
    log.info(
        'quote currency available: {cash}, cap: {cap}'.format(
            cash=cash,
            cap=context.MAX_HOLDINGS
        )
    )
    volume = data.current(context.asset, 'volume')
    price_change = (price - context.base_price) / context.base_price
    record(
        price=price,
        price_change=price_change,
        rsi=rsi,
        volume=volume,
        cash=cash,
        starting_cash=context.portfolio.starting_cash,
        leverage=context.account.leverage,
    )

    _handle_buy_sell_decision(context, data, signal, price)


def handle_data(context, data):
    dt = data.current_dt

    if context.last_bar is None or (
            context.last_bar + timedelta(minutes=15)) <= dt:
        context.last_bar = dt
    else:
        return

    log.info('BAR {}'.format(dt))
    try:
        _handle_data_rsi_only(context, data)
    except Exception as e:
        log.warn('aborting the bar on error {}'.format(e))
        context.errors.append(e)

    if len(context.errors) > 0:
        log.info('the errors:\n{}'.format(context.errors))


def analyze(context=None, results=None):
    import matplotlib.pyplot as plt

    quote_currency = list(context.exchanges.values())[0].quote_currency.upper()
    # Plot the portfolio and asset data.
    ax1 = plt.subplot(611)
    results.loc[:, 'portfolio_value'].plot(ax=ax1)
    ax1.set_ylabel('Portfolio Value ({})'.format(quote_currency))

    ax2 = plt.subplot(612, sharex=ax1)
    results.loc[:, 'price'].plot(ax=ax2)
    ax2.set_ylabel('{asset} ({quote})'.format(
        asset=context.asset.symbol, quote=quote_currency
    ))

    trans = results.loc[[t != [] for t in results.transactions], :]
    buys = trans.loc[[t[0]['amount'] > 0 for t in trans.transactions], :]
    sells = trans.loc[[t[0]['amount'] < 0 for t in trans.transactions], :]
    # buys = results.loc[results['action'] == 1, :]
    # sells = results.loc[results['action'] == 0, :]

    ax2.plot(
        buys.index,
        results.loc[buys.index, 'price'],
        '^',
        markersize=10,
        color='g',
    )
    ax2.plot(
        sells.index,
        results.loc[sells.index, 'price'],
        'v',
        markersize=10,
        color='r',
    )

    ax3 = plt.subplot(613, sharex=ax1)
    results.loc[:, ['alpha', 'beta']].plot(ax=ax3)
    ax3.set_ylabel('Alpha / Beta ')

    ax4 = plt.subplot(614, sharex=ax1)
    results.loc[:, ['starting_cash', 'cash']].plot(ax=ax4)
    ax4.set_ylabel('Quote Currency ({})'.format(quote_currency))

    results['algorithm'] = results.loc[:, 'algorithm_period_return']

    ax5 = plt.subplot(615, sharex=ax1)
    results.loc[:, ['algorithm', 'price_change']].plot(ax=ax5)
    ax5.set_ylabel('Percent Change')

    ax6 = plt.subplot(616, sharex=ax1)
    results.loc[:, 'rsi'].plot(ax=ax6)
    ax6.set_ylabel('RSI')

    ax6.plot(
        buys.index,
        results.loc[buys.index, 'rsi'],
        '^',
        markersize=10,
        color='g',
    )
    ax6.plot(
        sells.index,
        results.loc[sells.index, 'rsi'],
        'v',
        markersize=10,
        color='r',
    )

    plt.legend(loc=3)

    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()
    pass


if __name__ == '__main__':
    # Backtest
    run_algorithm(
        capital_base=0.5,
        data_frequency='minute',
        initialize=initialize,
        handle_data=handle_data,
        analyze=analyze,
        exchange_name='poloniex',
        algo_namespace=algo_namespace,
        quote_currency='btc',
        start=pd.to_datetime('2017-9-1', utc=True),
        end=pd.to_datetime('2017-10-1', utc=True),
    )
