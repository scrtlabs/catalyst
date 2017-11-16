"""
Requires Catalyst version 0.3.0 or above
Tested on Catalyst version 0.3.3

These example aims to provide and easy way for users to learn how to collect data from the different exchanges.
You simply need to specify the exchange and the market that you want to focus on.
You will all see how to create a universe and filter it base on the exchange and the market you desire.

The example prints out the closing price of all the pairs for a given market-exchange every 30 minutes.
The example also contains the ohlcv minute data for the past seven days which could be used to create indicators
Use this as the backbone to create your own trading strategies.

Variables lookback date and date are used to ensure data for a coin existed on the lookback period specified.
"""

import numpy as np
import pandas as pd
from datetime import timedelta
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

    # current date formatted into a string
    today = context.blotter.current_dt
    date, time = today.strftime('%Y-%m-%d %H:%M:%S').split(' ')
    lookback_date = today - timedelta(days=(
    lookback / (60 * 24)))  # subtract the amount of days specified in lookback
    lookback_date = lookback_date.strftime('%Y-%m-%d %H:%M:%S').split(' ')[
        0]  # get only the date as a string

    # update universe everyday
    new_day = 60 * 24
    if not context.i % new_day:
        context.universe = universe(context, lookback_date, date)

    # get data every 30 minutes
    minutes = 30
    if not context.i % minutes and context.universe:
        # we iterate for every pair in the current universe
        for coin in context.coins:
            pair = str(coin.symbol)

            # 30 minute interval ohlcv data (the standard data required for candlestick or indicators/signals)
            # 30T means 30 minutes re-sampling of one minute data. change to your desire time interval.
            opened = fill(data.history(coin, 'open', bar_count=lookback,
                                       frequency='30T')).values
            high = fill(data.history(coin, 'high', bar_count=lookback,
                                     frequency='30T')).values
            low = fill(data.history(coin, 'low', bar_count=lookback,
                                    frequency='30T')).values
            close = fill(data.history(coin, 'price', bar_count=lookback,
                                      frequency='30T')).values
            volume = fill(data.history(coin, 'volume', bar_count=lookback,
                                       frequency='30T')).values

            # close[-1] is the equivalent to current price
            # displays the minute price for each pair every 30 minutes
            print(
            today, pair, opened[-1], high[-1], low[-1], close[-1], volume[-1])

            # ----------------------------------------------------------------------------------------------------------
            # -------------------------------------- Insert Your Strategy Here -----------------------------------------
            # ----------------------------------------------------------------------------------------------------------


def analyze(context=None, results=None):
    pass


# Get the universe for a given exchange and a given base_currency market
# Example: Poloniex btc Market
def universe(context, lookback_date, current_date):
    json_symbols = get_exchange_symbols(
        context.exchange)  # get all the pairs for the exchange
    universe_df = pd.DataFrame.from_dict(json_symbols).transpose().astype(
        str)  # convert into a dataframe
    universe_df['base_currency'] = universe_df.apply(
        lambda row: row.symbol.split('_')[1],
        axis=1)
    universe_df['market_currency'] = universe_df.apply(
        lambda row: row.symbol.split('_')[0],
        axis=1)
    # Filter all the exchange pairs to only the ones for a give base currency
    universe_df = universe_df[
        universe_df['base_currency'] == context.base_currency]

    # Filter all the pairs to ensure that pair existed in the current date range
    universe_df = universe_df[universe_df.start_date < lookback_date]
    universe_df = universe_df[universe_df.end_daily >= current_date]
    context.coins = symbols(
        *universe_df.symbol)  # convert all the pairs to symbols
    return universe_df.symbol.tolist()


# Replace all NA, NAN or infinite values with its nearest value
def fill(series):
    if isinstance(series, pd.Series):
        return series.replace([np.inf, -np.inf], np.nan).ffill().bfill()
    elif isinstance(series, np.ndarray):
        return pd.Series(series).replace([np.inf, -np.inf],
                                         np.nan).ffill().bfill().values
    else:
        return series


if __name__ == '__main__':
    start_date = pd.to_datetime('2017-01-08', utc=True)
    end_date = pd.to_datetime('2017-11-13', utc=True)

    performance = run_algorithm(start=start_date, end=end_date,
                                capital_base=10000.0,
                                initialize=initialize,
                                handle_data=handle_data,
                                analyze=analyze,
                                exchange_name='poloniex',
                                data_frequency='minute',
                                base_currency='btc',
                                live=False,
                                live_graph=False,
                                algo_namespace='simple_universe')

"""
Run in Terminal (inside catalyst environment):
python simple_universe.py
"""
