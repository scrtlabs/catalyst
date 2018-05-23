# For this example, we're going to write a simple momentum script.  When the
# stock goes up quickly, we're going to buy; when it goes down quickly, we're
# going to sell.  Hopefully we'll ride the waves.
import os
import tempfile
import time

import pandas as pd
import talib
from logbook import Logger

from catalyst import run_algorithm
from catalyst.api import symbol, record, order_target_percent, get_dataset
from catalyst.exchange.utils.stats_utils import set_print_settings, \
    get_pretty_stats
# We give a name to the algorithm which Catalyst will use to persist its state.
# In this example, Catalyst will create the `.catalyst/data/live_algos`
# directory. If we stop and start the algorithm, Catalyst will resume its
# state using the files included in the folder.
from catalyst.utils.paths import ensure_directory

NAMESPACE = 'mean_reversion_simple'
log = Logger(NAMESPACE)


# To run an algorithm in Catalyst, you need two functions: initialize and
# handle_data.

def initialize(context):
    # This initialize function sets any data or variables that you'll use in
    # your algorithm.  For instance, you'll want to define the trading pair (or
    # trading pairs) you want to backtest.  You'll also want to define any
    # parameters or values you're going to use.

    # In our example, we're looking at Neo in Ether.
    df = get_dataset('testmarketcap2')  # type: pd.DataFrame

    # Picking a specific date in our DataFrame
    first_dt = df.index.get_level_values(0)[0]
    # Since we use a MultiIndex with date / symbol, picking a date will
    # result in a new DataFrame for the selected date with a single
    # symbol index
    df = df.xs(first_dt, level=0)
    # Keep only the top coins by market cap
    df = df.loc[df['market_cap_usd'].isin(df['market_cap_usd'].nlargest(100))]

    set_print_settings()

    df.sort_values(by=['market_cap_usd'], ascending=True, inplace=True)
    print('the marketplace data:\n{}'.format(df))

    # Pick the 5 assets with the lowest market cap for trading
    quote_currency = 'eth'
    exchange = context.exchanges[next(iter(context.exchanges))]
    symbols = [a.symbol for a in exchange.assets
               if a.start_date < context.datetime]
    context.assets = []
    for currency, price in df['market_cap_usd'].iteritems():
        if len(context.assets) >= 5:
            break

        s = '{}_{}'.format(currency.decode('utf-8'), quote_currency)
        if s in symbols:
            context.assets.append(symbol(s))

    context.base_price = None
    context.current_day = None

    context.RSI_OVERSOLD = 55
    context.RSI_OVERBOUGHT = 60
    context.CANDLE_SIZE = '5T'

    context.start_time = time.time()


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
        context.traded_today = dict()
        context.current_day = today

    # Preparing dictionaries for asset-level data points
    volumes = dict()
    rsis = dict()
    price_values = dict()
    cash = context.portfolio.cash

    for asset in context.assets:
        # We're computing the volume-weighted-average-price of the security
        # defined above, in the context.assets variable.  For this example,
        #  we're using three bars on the 15 min bars.

        # The frequency attribute determine the bar size. We use this
        # convention for the frequency alias:
        # http://pandas.pydata.org/pandas-docs/stable/timeseries.html#offset-aliases
        prices = data.history(
            asset,
            fields='close',
            bar_count=50,
            frequency=context.CANDLE_SIZE
        )

        # Ta-lib calculates various technical indicator based on price and
        # volume arrays.

        # In this example, we are comp
        rsi = talib.RSI(prices.values, timeperiod=14)

        # We need a variable for the current price of the security to compare
        #  to the average. Since we are requesting two fields, data.current()
        # returns a DataFrame with
        current = data.current(asset, fields=['close', 'volume'])
        price = current['close']

        # If base_price is not set, we use the current value. This is the
        # price at the first bar which we reference to calculate price_change.
        # if asset not in context.base_price:
        #     context.base_price[asset] = price
        #
        # base_price = context.base_price[asset]
        # price_change = (price - base_price) / base_price

        # Tracking the relevant data
        volumes[asset] = current['volume']
        rsis[asset] = rsi[-1]
        price_values[asset] = price
        # price_changes[asset] = price_change

        # We are trying to avoid over-trading by limiting our trades to
        # one per day.
        if asset in context.traded_today:
            continue

        # Exit if we cannot trade
        if not data.can_trade(asset):
            continue

        # Another powerful built-in feature of the Catalyst backtester is the
        # portfolio object.  The portfolio object tracks your positions, cash,
        # cost basis of specific holdings, and more.  In this line, we
        # calculate how long or short our position is at this minute.
        pos_amount = context.portfolio.positions[asset].amount

        if rsi[-1] <= context.RSI_OVERSOLD and pos_amount == 0:
            log.info(
                '{}: buying - price: {}, rsi: {}'.format(
                    data.current_dt, price, rsi[-1]
                )
            )
            # Set a style for limit orders,
            limit_price = price * 1.005
            target = 1.0 / len(context.assets)
            order_target_percent(
                asset, target, limit_price=limit_price
            )
            context.traded_today[asset] = True

        elif rsi[-1] >= context.RSI_OVERBOUGHT and pos_amount > 0:
            log.info(
                '{}: selling - price: {}, rsi: {}'.format(
                    data.current_dt, price, rsi[-1]
                )
            )
            limit_price = price * 0.995
            order_target_percent(
                asset, 0, limit_price=limit_price
            )
            context.traded_today[asset] = True

    # Now that we've collected all current data for this frame, we use
    # the record() method to save it. This data will be available as
    # a parameter of the analyze() function for further analysis.
    record(
        current_price=price_values,
        volume=volumes,
        rsi=rsis,
        cash=cash,
    )


def analyze(context=None, perf=None):
    stats = get_pretty_stats(perf)
    print('the algo stats:\n{}'.format(stats))
    pass


if __name__ == '__main__':
    # The execution mode: backtest or live
    live = False

    if live:
        run_algorithm(
            capital_base=0.1,
            initialize=initialize,
            handle_data=handle_data,
            analyze=analyze,
            exchange_name='poloniex',
            live=True,
            algo_namespace=NAMESPACE,
            quote_currency='btc',
            live_graph=False,
            simulate_orders=False,
            stats_output=None,
        )

    else:
        folder = os.path.join(
            tempfile.gettempdir(), 'catalyst', NAMESPACE
        )
        ensure_directory(folder)

        timestr = time.strftime('%Y%m%d-%H%M%S')
        out = os.path.join(folder, '{}.p'.format(timestr))
        # catalyst run -f catalyst/examples/mean_reversion_simple.py \
        #    -x bitfinex -s 2017-10-1 -e 2017-11-10 -c usdt -n mean-reversion \
        #   --data-frequency minute --capital-base 10000
        run_algorithm(
            capital_base=100,
            data_frequency='minute',
            initialize=initialize,
            handle_data=handle_data,
            analyze=analyze,
            exchange_name='poloniex',
            algo_namespace=NAMESPACE,
            quote_currency='eth',
            start=pd.to_datetime('2017-10-01', utc=True),
            end=pd.to_datetime('2017-10-15', utc=True),
        )
        log.info('saved perf stats: {}'.format(out))
