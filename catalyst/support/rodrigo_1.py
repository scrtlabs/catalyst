import pandas as pd
from logbook import Logger, DEBUG

from catalyst import run_algorithm
from catalyst.api import (schedule_function, order_target_percent, symbol,
                          date_rules, get_open_orders, cancel_order, record,
                          set_commission, set_slippage)

log = Logger('rodrigo_1', level=DEBUG)
"""
The initialize function sets any data or variables that 
you'll use in your algorithm. 
It's only called once at the beginning of your algorithm.
"""


def initialize(context):
    # Select asset of interest
    context.asset = symbol('BTC_USD')

    # set_commission(TradingPairFeeSchedule(maker_fee=0.5, taker_fee=0.5))
    # set_slippage(TradingPairFixedSlippage(spread=0.5))
    # Set up a rebalance method to run every day
    schedule_function(rebalance, date_rule=date_rules.every_day())


"""
Rebalance function scheduled to run once per day.
"""


def rebalance(context, data):
    # To make market decisions, we're calculating the token's
    # moving average for the last 5 days.

    # We get the price history for the last 5 days.
    price_history = data.history(context.asset, fields='price', bar_count=5,
                                 frequency='1d')

    # Then we take an average of those 5 days.
    average_price = price_history.mean()

    # We also get the coin's current price.
    price = data.current(context.asset, 'price')

    # Cancel any outstanding orders
    orders = get_open_orders(context.asset) or []
    for order in orders:
        cancel_order(order)

    # If our coin is currently listed on a major exchange
    if data.can_trade(context.asset):
        # If the current price is 1% above the 5-day average price,
        # we open a long position. If the current price is below the
        # average price, then we want to close our position to 0 shares.
        if price > (1.01 * average_price):
            # Place the buy order (positive means buy, negative means sell)
            order_target_percent(context.asset, .99)
            log.info("Buying %s" % (context.asset.symbol))
        elif price < average_price:
            # Sell all of our shares by setting the target position to zero
            order_target_percent(context.asset, 0)
            log.info("Selling %s" % (context.asset.symbol))

    # Use the record() method to track up to five custom signals.
    # Record Apple's current price and the average price over the last
    # five days.
    cash = context.portfolio.cash
    leverage = context.account.leverage

    record(price=price, average_price=average_price, cash=cash,
           leverage=leverage)


def analyze(context=None, results=None):
    import matplotlib.pyplot as plt

    # Plot the portfolio and asset data.
    ax1 = plt.subplot(511)
    results[['portfolio_value']].plot(ax=ax1)
    ax1.set_ylabel('Portfolio Value (USD)')

    ax2 = plt.subplot(512, sharex=ax1)
    ax2.set_ylabel('{asset} (USD)'.format(asset=context.asset))
    (results[[
        'price',
    ]]).plot(ax=ax2)

    trans = results.ix[[t != [] for t in results.transactions]]
    buys = trans.ix[
        [t[0]['amount'] > 0 for t in trans.transactions]
    ]
    sells = trans.ix[
        [t[0]['amount'] < 0 for t in trans.transactions]
    ]

    ax2.plot(
        buys.index,
        results.price[buys.index],
        '^',
        markersize=10,
        color='g',
    )
    ax2.plot(
        sells.index,
        results.price[sells.index],
        'v',
        markersize=10,
        color='r',
    )

    ax3 = plt.subplot(513, sharex=ax1)
    results[['leverage']].plot(ax=ax3)
    ax3.set_ylabel('Leverage ')

    ax4 = plt.subplot(514, sharex=ax1)
    results[['cash']].plot(ax=ax4)
    ax4.set_ylabel('Cash (USD)')

    results[[
        'algorithm',
        'benchmark',
    ]] = results[[
        'algorithm_period_return',
        'benchmark_period_return',
    ]]

    ax5 = plt.subplot(515, sharex=ax1)
    results[[
        'algorithm',
        'benchmark',
    ]].plot(ax=ax5)
    ax5.set_ylabel('Percent Change')

    plt.legend(loc=3)

    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()


run_algorithm(
    capital_base=100000,
    start=pd.to_datetime('2017-1-1', utc=True),
    end=pd.to_datetime('2017-10-22', utc=True),
    data_frequency='minute',
    initialize=initialize,
    handle_data=None,
    analyze=analyze,
    exchange_name='bitfinex',
    algo_namespace='rodrigo_1',
    base_currency='usd'
)
