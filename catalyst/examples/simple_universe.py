"""
Requires Catalyst version 0.3.0 or above
Tested on Catalyst version 0.3.2

These example aims to provide and easy way for users to learn how to collect data from the different exchanges.
You simply need to specify the exchange and the market that you want to focus on.
You will all see how to create a universe and filter it base on the exchange and the market you desire.

The example prints out the closing price of all the pairs for a given market-exchange every 30 minutes.
The example also contains the ohlcv minute data for the past seven days which could be used to create indicators
Use this as the backbone to create your own trading strategies.
"""

import pandas as pd
from catalyst import run_algorithm
from catalyst.exchange.exchange_utils import get_exchange_symbols

from catalyst.api import (
    symbols,
)


def initialize(context):
    context.i = -1  # counts the minutes
    context.exchange = 'poloniex'  # must match the exchange specified in run_algorithm
    context.base_currency = 'btc'  # must match the base currency specified in run_algorithm


def handle_data(context, data):
    lookback = 60 * 24 * 7  # (minutes, hours, days) of how far to lookback in the data history
    context.i += 1

    # we must first wait until enough minutes, hours or days have passed for data history to work
    if context.i < lookback:
        return

    # current date formatted into a string
    today = context.blotter.current_dt.strftime('%Y-%m-%d %H:%M:%S')
    date, time = str(today).split(' ')

    # update universe everyday
    new_day = 60 * 24
    if not context.i % new_day:
        context.universe = universe(context, date)

    # get data every 30 minutes
    minutes = 30
    if not context.i % minutes and context.universe:
        # we iterate for every pair in the current universe
        for coin in context.coins:
            pair = str(coin.symbol)

            # ohlcv data (the standard data required for candlestick or indicators/signals)
            open = data.history(coin, 'open', bar_count=lookback, frequency='1m').ffill().bfill()
            high = data.history(coin, 'high', bar_count=lookback, frequency='1m').ffill().bfill()
            low = data.history(coin, 'low', bar_count=lookback, frequency='1m').ffill().bfill()
            close = data.history(coin, 'price', bar_count=lookback, frequency='1m').ffill().bfill()
            volume = data.history(coin, 'volume', bar_count=lookback, frequency='1m').ffill().bfill()

            # close[-1] is the equivalent to current price
            # displays the minute price for each pair every 30 minutes
            print(today, pair, close[-1])


def analyze(context=None, results=None):
    pass


def universe(context, date):
    # Get the universe for a given exchange and a given base_currency market
    # Example: Poloniex BTC Market
    json_symbols = get_exchange_symbols(context.exchange)  # get all the pairs for the exchange
    poloniex_universe_df = pd.DataFrame.from_dict(json_symbols).transpose().astype(str)  # convert into a dataframe
    poloniex_universe_df['base_currency'] = poloniex_universe_df.apply(lambda row: row.symbol.split('_')[1],
                                                                       axis=1)
    poloniex_universe_df['market_currency'] = poloniex_universe_df.apply(lambda row: row.symbol.split('_')[0],
                                                                         axis=1)
    # Filter all the exchange pairs to only the ones for a give base currency
    poloniex_universe_df = poloniex_universe_df[poloniex_universe_df['base_currency'] == context.base_currency]

    # Filter all the pairs to ensure that pair existed in the current date
    poloniex_universe_df = poloniex_universe_df[poloniex_universe_df.start_date < date]
    context.coins = symbols(*poloniex_universe_df.symbol)  # convert all the pairs to symbols
    return poloniex_universe_df.symbol.tolist()


if __name__ == '__main__':
    start_date = pd.to_datetime('2017-01-01', utc=True)
    end_date = pd.to_datetime('2017-10-15', utc=True)

    performance = run_algorithm(start=start_date, end=end_date,
                                capital_base=10000.0,
                                initialize=initialize,
                                handle_data=handle_data,
                                analyze=analyze,
                                exchange_name='poloniex',
                                bundle='poloniex',
                                data_frequency='minute',
                                base_currency='btc',
                                live=False,
                                live_graph=False,
                                algo_namespace='simple_universe')

"""
Run in Terminal (inside catalyst environment):
python simple_universe.py
"""
