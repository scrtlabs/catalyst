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
from catalyst.exchange.stats_utils import crossunder, get_pretty_stats, \
    extract_transactions

algo_namespace = 'momentum'
log = Logger(algo_namespace)


def initialize(context):
    # This initialize function sets any data or variables that you'll use in
    # your algorithm.  For instance, you'll want to define the trading pair (or
    # trading pairs) you want to backtest.  You'll also want to define any
    # parameters or values you're going to use.

    # In our example, we're looking at Ether in USD Tether.
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
    # would only execute once. This method works with minute and daily
    # frequencies.
    today = data.current_dt.floor('1D')
    if today != context.current_day:
        context.traded_today = False
        context.current_day = today

    # We're computing the volume-weighted-average-price of the security
    # defined above, in the context.eth_btc variable.  For this example, we're 
    # using three bars on the 15 min bars.

    # The frequency attribute determine the bar size. We use this convention
    # for the frequency alias:
    # http://pandas.pydata.org/pandas-docs/stable/timeseries.html#offset-aliases
    prices = data.history(
        context.eth_btc,
        fields='close',
        bar_count=220,
        frequency='15T'
    )

    # Ta-lib calculates various technical indicator based on price and
    # volume arrays.

    # In this example, we are comp
    rsi = talib.RSI(prices.values, timeperiod=4)
    sma200 = talib.SMA(prices.values, timeperiod=200)

    # We need a variable for the current price of the security to compare to
    # the average. Since we are requesting two fields, data.current()
    # returns a DataFrame with
    current = data.current(context.eth_btc, fields=['close', 'volume'])
    price = current['close']
    log.info(
        '{}: price: {}, rsi: {}, sma: {}'.format(
            data.current_dt, price, rsi[-1], sma200[-1]
        )
    )

    # If base_price is not set, we use the current value. This is the
    # price at the first bar which we reference to calculate price_change.
    if context.base_price is None:
        context.base_price = price

    price_change = (price - context.base_price) / context.base_price
    cash = context.portfolio.cash

    # Now that we've collected all current data for this frame, we use
    # the record() method to save it. This data will be available as
    # a parameter of the analyze() function for further analysis.
    record(
        price=price,
        volume=current['volume'],
        sma200=sma200[-1],
        price_change=price_change,
        rsi=rsi[-1],
        cash=cash
    )

    # We are trying to avoid over-trading by limiting our trades to
    # one per day.
    if context.traded_today:
        log.info('skipping because we\'ve already trader today')
        return

    # Since we are using limit orders, some orders may not execute immediately
    # we wait until all orders are executed before considering more trades.
    orders = get_open_orders(context.eth_btc)
    if len(orders) > 0:
        log.info('skipping until all open orders execute')
        return

    # Another powerful built-in feature of the Catalyst backtester is the
    # portfolio object.  The portfolio object tracks your positions, cash,
    # cost basis of specific holdings, and more.  In this line, we calculate
    # how long or short our position is at this minute.   
    pos_amount = context.portfolio.positions[context.eth_btc].amount

    # Determining the entry and exit signals based on RSI and SMA
    if rsi[-1] <= 30 and data.can_trade(context.eth_btc) \
            and pos_amount == 0:
        # and price > sma200[-1] and pos_amount == 0:
        order_target_percent(context.eth_btc, 1)
        context.traded_today = True

    elif (rsi[-1] >= 90 or crossunder(prices, sma200)) \
            and data.can_trade(context.eth_btc) and pos_amount > 0:
        order_target_percent(context.eth_btc, 0)
        context.traded_today = True


def analyze(context=None, perf=None):
    import matplotlib.pyplot as plt

    # The base currency of the algo exchange
    base_currency = context.exchanges.values()[0].base_currency.upper()

    # Plot the portfolio value over time.
    ax1 = plt.subplot(611)
    perf.loc[:, 'portfolio_value'].plot(ax=ax1)
    ax1.set_ylabel('Portfolio Value ({})'.format(base_currency))

    # Plot the price increase or decrease over time.
    ax2 = plt.subplot(612, sharex=ax1)
    perf.loc[:, 'price'].plot(ax=ax2, label='Price')
    perf.loc[:, 'sma200'].plot(ax=ax2, label='SMA200')

    ax2.set_ylabel('{asset} ({base})'.format(
        asset=context.eth_btc.symbol, base=base_currency
    ))

    transaction_df = extract_transactions(perf)
    buy_df = transaction_df[transaction_df['amount'] > 0]
    sell_df = transaction_df[transaction_df['amount'] < 0]
    ax2.scatter(
        buy_df.index,
        perf.loc[buy_df.index, 'price'],
        marker='^',
        s=100,
        c='green',
        label=''
    )
    ax2.scatter(
        sell_df.index,
        perf.loc[sell_df.index, 'price'],
        marker='v',
        s=100,
        c='red',
        label=''
    )

    ax4 = plt.subplot(613, sharex=ax1)
    perf.loc[:, 'cash'].plot(
        ax=ax4, label='Base Currency ({})'.format(base_currency)
    )
    ax4.set_ylabel('Cash ({})'.format(base_currency))

    perf['algorithm'] = perf.loc[:, 'algorithm_period_return']

    ax5 = plt.subplot(614, sharex=ax1)
    perf.loc[:, ['algorithm', 'price_change']].plot(ax=ax5)
    ax5.set_ylabel('Percent Change')

    ax6 = plt.subplot(615, sharex=ax1)
    perf.loc[:, 'rsi'].plot(ax=ax6, label='RSI')
    ax6.axhline(70, color='darkgoldenrod')
    ax6.axhline(30, color='darkgoldenrod')
    ax6.scatter(
        buy_df.index,
        perf.loc[buy_df.index, 'rsi'],
        marker='^',
        s=100,
        c='green',
        label=''
    )
    ax6.scatter(
        sell_df.index,
        perf.loc[sell_df.index, 'rsi'],
        marker='v',
        s=100,
        c='red',
        label=''
    )
    plt.legend(loc=3)

    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()
    pass


if __name__ == '__main__':
    # The execution mode: backtest or live
    MODE = 'backtest'

    if MODE == 'backtest':
        run_algorithm(
            capital_base=1,
            data_frequency='minute',
            initialize=initialize,
            handle_data=handle_data,
            analyze=analyze,
            exchange_name='poloniex',
            algo_namespace=algo_namespace,
            base_currency='usdt',
            start=pd.to_datetime('2017-7-1', utc=True),
            end=pd.to_datetime('2017-9-30', utc=True),
            # end=pd.to_datetime('2017-7-7', utc=True),
        )

    elif MODE == 'live':
        run_algorithm(
            initialize=initialize,
            handle_data=handle_data,
            analyze=analyze,
            exchange_name='poloniex',
            live=True,
            algo_namespace=algo_namespace,
            base_currency='usdt',
            live_graph=True
        )
