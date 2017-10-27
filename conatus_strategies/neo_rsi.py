import talib
import pandas as pd
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

algo_namespace = 'neo_rsi'
log = Logger(algo_namespace)


def initialize(context):
    log.info('initializing algo')
    context.asset = symbol('neo_usd', 'bitfinex')

    context.BUY_SIGNAL = 30
    context.SELL_SIGNAL = 70
    context.SLIPPAGE_ALLOWED = 0.02

    context.errors = []
    pass


def _handle_data(context, data):
    dt = data.current_dt
    log.info('BAR {}'.format(dt))

    price = data.current(context.asset, 'close')
    log.info('got price {price}'.format(price=price))

    if price is None:
        log.warn('no pricing data')
        return

    try:
        prices = data.history(
            context.asset,
            fields='price',
            bar_count=15,
            frequency='15m'
        )
    except Exception as e:
        log.warn('historical data not available: '.format(e))
        return

    rsi = talib.RSI(prices.values, timeperiod=14)[-1]
    log.info('got rsi: {}'.format(rsi))

    cash = context.portfolio.cash
    log.info('base currency available: {cash}'.format(cash=cash))


    orders = get_open_orders(context.asset)
    # if len(orders) > 0:
    #     log.info('skipping bar until all open orders execute')
    #     return

    if context.asset in context.portfolio.positions:
        if rsi >= context.SELL_SIGNAL:
            position = context.portfolio.positions[context.asset]
            log.info('closing position')
            amount = -position.amount
            expected_proceeds = -(amount * price)
            order(
                asset=context.asset,
                amount=amount,
                limit_price=price * (1 - context.SLIPPAGE_ALLOWED),
            )
    else:
        if rsi <= context.BUY_SIGNAL:
            log.info('opening position')
            order(
                asset=context.asset,
                amount=cash / price,
                limit_price=price * (1 + context.SLIPPAGE_ALLOWED),
            )

    volume = data.current(context.asset, 'volume')
    record(
        price=price,
        volume=volume,
        cash=cash,
        starting_cash=context.portfolio.starting_cash,
        leverage=context.account.leverage,
        rsi=rsi
    )


def handle_data(context, data):
    try:
        _handle_data(context, data)
    except Exception as e:
        log.warn('aborting the bar on error {}'.format(e))
        context.errors.append(e)

    log.debug('completed bar {}, total execution errors {}'.format(
        data.current_dt,
        len(context.errors)
    ))

    if len(context.errors) > 0:
        log.info('the errors:\n{}'.format(context.errors))


def analyze(context=None, results=None):
    import matplotlib.pyplot as plt

    # Plot the portfolio and asset data.
    ax1 = plt.subplot(611)
    results[['portfolio_value']].plot(ax=ax1)
    ax1.set_ylabel('Portfolio Value (USD)')

    ax2 = plt.subplot(612, sharex=ax1)
    ax2.set_ylabel('{asset} (USD)'.format(asset=context.asset.symbol))
    (results[['price']]).plot(ax=ax2)

    trans = results.ix[[t != [] for t in results.transactions]]
    buys = trans.ix[
        [t[0]['amount'] > 0 for t in trans.transactions]
    ]
    ax2.plot(
        buys.index,
        results.price[buys.index],
        '^',
        markersize=10,
        color='g',
    )

    ax3 = plt.subplot(613, sharex=ax1)
    results[['leverage', 'alpha', 'beta']].plot(ax=ax3)
    ax3.set_ylabel('Leverage ')

    ax4 = plt.subplot(614, sharex=ax1)
    results[['starting_cash', 'cash']].plot(ax=ax4)
    ax4.set_ylabel('Cash (USD)')

    results[[
        'treasury',
        'algorithm',
        'benchmark',
    ]] = results[[
        'treasury_period_return',
        'algorithm_period_return',
        'benchmark_period_return',
    ]]

    ax5 = plt.subplot(615, sharex=ax1)
    results[[
        'treasury',
        'algorithm',
        'benchmark',
    ]].plot(ax=ax5)
    ax5.set_ylabel('Percent Change')

    ax6 = plt.subplot(616, sharex=ax1)
    results[['volume']].plot(ax=ax6)
    ax6.set_ylabel('Volume (mCoins/5min)')

    plt.legend(loc=3)

    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()
    pass


# run_algorithm(
#     initialize=initialize,
#     handle_data=handle_data,
#     analyze=analyze,
#     exchange_name='bitfinex',
#     live=True,
#     algo_namespace=algo_namespace,
#     base_currency='btc',
#     live_graph=False
# )

# Backtest
run_algorithm(
    capital_base=10000,
    data_frequency='minute',
    initialize=initialize,
    handle_data=handle_data,
    analyze=analyze,
    exchange_name='bitfinex',
    algo_namespace=algo_namespace,
    base_currency='usd',
    start=pd.to_datetime('2017-9-10', utc=True),
    end=pd.to_datetime('2017-10-22', utc=True),
)
