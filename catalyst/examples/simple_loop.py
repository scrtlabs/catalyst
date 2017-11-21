import talib
import pandas as pd

from catalyst import run_algorithm
from catalyst.api import symbol, record
from catalyst.exchange.stats_utils import get_pretty_stats, \
    extract_transactions


def initialize(context):
    print('initializing')
    context.asset = symbol('neo_usd')
    context.base_price = None


def handle_data(context, data):
    print('handling bar: {}'.format(data.current_dt))

    price = data.current(context.asset, 'close')
    print('got price {price}'.format(price=price))

    try:
        prices = data.history(
            context.asset,
            fields='price',
            bar_count=14,
            frequency='15T'
        )
        rsi = talib.RSI(prices.values, timeperiod=14)[-1]
        print('got rsi: {}'.format(rsi))
    except Exception as e:
        print(e)

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
        price_change=price_change,
        cash=cash
    )


def analyze(context, perf):
    import matplotlib.pyplot as plt
    print('the stats: {}'.format(get_pretty_stats(perf)))

    # The base currency of the algo exchange
    base_currency = context.exchanges.values()[0].base_currency.upper()

    # Plot the portfolio value over time.
    ax1 = plt.subplot(611)
    perf.loc[:, 'portfolio_value'].plot(ax=ax1)
    ax1.set_ylabel('Portfolio Value ({})'.format(base_currency))

    # Plot the price increase or decrease over time.
    ax2 = plt.subplot(612, sharex=ax1)
    perf.loc[:, 'price'].plot(ax=ax2, label='Price')

    ax2.set_ylabel('{asset} ({base})'.format(
        asset=context.asset.symbol, base=base_currency
    ))

    transaction_df = extract_transactions(perf)
    if not transaction_df.empty:
        buy_df = transaction_df[transaction_df['amount'] > 0]
        sell_df = transaction_df[transaction_df['amount'] < 0]
        ax2.scatter(
            buy_df.index.to_pydatetime(),
            perf.loc[buy_df.index, 'price'],
            marker='^',
            s=100,
            c='green',
            label=''
        )
        ax2.scatter(
            sell_df.index.to_pydatetime(),
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

    plt.legend(loc=3)

    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()
    pass


run_algorithm(
    capital_base=250,
    start=pd.to_datetime('2017-11-1 0:00', utc=True),
    end=pd.to_datetime('2017-11-10 23:59', utc=True),
    data_frequency='daily',
    initialize=initialize,
    handle_data=handle_data,
    analyze=analyze,
    exchange_name='bitfinex',
    algo_namespace='simple_loop',
    base_currency='usd'
)
# run_algorithm(
#     initialize=initialize,
#     handle_data=handle_data,
#     analyze=None,
#     exchange_name='poloniex',
#     live=True,
#     algo_namespace='simple_loop',
#     base_currency='eth',
#     live_graph=False
