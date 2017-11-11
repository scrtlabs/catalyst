# For this example, we're going to write a simple momentum script.  When the 
# stock goes up quickly, we're going to buy; when it goes down quickly, we're
# going to sell.  Hopefully we'll ride the waves.
from collections import OrderedDict

import pandas as pd
import talib
# To run an algorithm in Catalyst, you need two functions: initialize and
# handle_data.
from logbook import Logger

from catalyst import run_algorithm
from catalyst.api import symbol, record, order_target_percent, \
    get_open_orders

# We give a name to the algorithm which Catalyst will use to persist its state.
# In this example, Catalyst will create the `.catalyst/data/live_algos`
# directory. If we stop and start the algorithm, Catalyst will resume its
# state using the files included in the folder.
algo_namespace = 'momentum'
log = Logger(algo_namespace)


def initialize(context):
    # This initialize function sets any data or variables that you'll use in
    # your algorithm.  For instance, you'll want to define the trading pair (or
    # trading pairs) you want to backtest.  You'll also want to define any
    # parameters or values you're going to use.

    # In our example, we're looking at Ether in Bitcoin.
    context.eth_btc = symbol('eth_usdt')
    context.max_amount = 0.01
    context.base_price = None
    context.current_day = None
    context.yesterdy = None


def handle_data(context, data):
    # This handle_data function is where the real work is done.  Our data is
    # minute-level tick data, and each minute is called a frame.  This function
    # runs on each frame of the data.

    # We flag the first period of each day.
    # Since cryptocurrencies trade 24/7 the `before_trading_starts` handle
    # would only execute once.
    today = data.current_dt.floor('1D')
    if today != context.current_day:
        context.traded_today = False
        context.current_day = today

    # We're computing the volume-weighted-average-price of the security
    # defined above, in the context.eth_btc variable.  For this example, we're 
    # using three bars on the daily chart.
    prices = data.history(
        context.eth_btc,
        fields='close',
        bar_count=100,
        frequency='30T'
    )
    # Use TA-Lib to calculate MACD data using calibrated settings
    macd_raw, signal, macd_hist = talib.MACD(
        prices.values, fastperiod=30, slowperiod=40, signalperiod=45
    )

    # We need a variable for the current price of the security to compare to
    # the average.
    current = data.current(context.eth_btc, fields=['close', 'volume'])
    price = current['close']
    log.info(
        '{}: price: {}, macd: {}'.format(data.current_dt, price, macd_raw[-1])
    )

    # If base_price is not set, we use the current value. This is the
    # price at the first bar which we reference to calculate price_change.
    if context.base_price is None:
        context.base_price = price
    price_change = (price - context.base_price) / context.base_price

    record(
        price=price,
        volume=current['volume'],
        macd=macd_raw[-1],
        signal=signal[-1],
        price_change=price_change,
    )

    orders = get_open_orders(context.eth_btc)
    if len(orders) > 0:
        log.info('skipping bar until all open orders execute')
        return

    # Another powerful built-in feature of the Catalyst backtester is the
    # portfolio object.  The portfolio object tracks your positions, cash,
    # cost basis of specific holdings, and more.  In this line, we calculate
    # how long or short our position is at this minute.   
    pos_amount = context.portfolio.positions[context.eth_btc].amount

    if macd_hist[-1] > 0 and data.can_trade(context.eth_btc) \
            and pos_amount == 0 and not context.traded_today:
        order_target_percent(context.eth_btc, 0.75)
        context.traded_today = True

    elif macd_hist[-1] < 0 and data.can_trade(context.eth_btc) \
            and pos_amount > 0 and not context.traded_today:
        order_target_percent(context.eth_btc, 0)
        context.traded_today = True


def analyze(context=None, results=None):
    import matplotlib.pyplot as plt

    # The base currency of the algo exchange
    base_currency = context.exchanges.values()[0].base_currency.upper()

    # Plot the portfolio value over time.
    ax1 = plt.subplot(611)
    results.loc[:, 'portfolio_value'].plot(ax=ax1)
    ax1.set_ylabel('Portfolio Value ({})'.format(base_currency))

    # Plot the price increase or decrease over time.
    ax2 = plt.subplot(612, sharex=ax1)
    results.loc[:, 'price'].plot(ax=ax2)
    ax2.set_ylabel('{asset} ({base})'.format(
        asset=context.eth_btc.symbol, base=base_currency
    ))

    # Compute indexes for buy and sell transactions
    trans_list = results.transactions.values
    all_trans = [t for sublist in trans_list for t in sublist]
    all_trans.sort(key=lambda t: t['dt'])

    buys = results.loc[[t['dt'] for t in all_trans if t['amount'] > 0], :]
    sells = results.loc[[t['dt'] for t in all_trans if t['amount'] < 0], :]

    ax2.scatter(
        buys.index,
        results.loc[buys.index, 'price'],
        marker='^',
        s=100,
        c='green',
    )
    ax2.scatter(
        sells.index,
        results.loc[sells.index, 'price'],
        marker='v',
        s=100,
        c='red',
    )

    ax4 = plt.subplot(613, sharex=ax1)
    results.loc[:, ['starting_cash', 'cash']].plot(ax=ax4)
    ax4.set_ylabel('Base Currency ({})'.format(base_currency))

    results['algorithm'] = results.loc[:, 'algorithm_period_return']

    ax5 = plt.subplot(614, sharex=ax1)
    results.loc[:, ['algorithm', 'price_change']].plot(ax=ax5)
    ax5.set_ylabel('Percent Change')

    ax6 = plt.subplot(615, sharex=ax1)
    results.loc[:, 'macd'].plot(ax=ax6, label='macd')

    ax6.scatter(
        buys.index,
        results.loc[buys.index, 'macd'],
        marker='^',
        s=100,
        c='green',
        label=''
    )
    ax6.scatter(
        sells.index,
        results.loc[sells.index, 'macd'],
        marker='v',
        s=100,
        c='red',
        label=''
    )
    # handles, labels = plt.gca().get_legend_handles_labels()
    # i = 1
    # while i < len(labels):
    #     if labels[i] in labels[:i]:
    #         del (labels[i])
    #         del (handles[i])
    #     else:
    #         i += 1

    plt.legend(loc=3)

    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()
    pass


# Backtest
run_algorithm(
    capital_base=1,
    data_frequency='minute',
    initialize=initialize,
    handle_data=handle_data,
    analyze=analyze,
    exchange_name='poloniex',
    algo_namespace=algo_namespace,
    base_currency='usdt',
    start=pd.to_datetime('2017-6-1', utc=True),
    end=pd.to_datetime('2017-6-7', utc=True),
)
