"""
Requires Catalyst version 0.3.0 or above
Tested on Catalyst version 0.3.3

This example aims to provide an easy way for users to learn how to
collect data from any given exchange and select a subset of the available
currency pairs for trading. You simply need to specify the exchange and
the market (quote_currency) that you want to focus on. You will then see
how to create a universe of assets, and filter it based the market you
desire.

The example prints out the closing price of all the pairs for a given
market in a given exchange every 30 minutes. The example also contains
the OHLCV data with minute-resolution for the past seven days which
could be used to create indicators. Use this code as the backbone to
create your own trading strategy.

The lookback_date variable is used to ensure data for a coin existed on
the lookback period specified.

To run, execute the following two commands in a terminal (inside catalyst
environment). The first one retrieves all the pricing data needed for this
script to run (only needs to be run once), and the second one executes this
script with the parameters specified in the run_algorithm() call at the end
of the file:

catalyst ingest-exchange -x bitfinex -f minute

python simple_universe.py

"""
from datetime import timedelta

import numpy as np
import pandas as pd

from catalyst import run_algorithm
from catalyst.api import (symbols, )
from catalyst.exchange.utils.exchange_utils import get_exchange_symbols


def initialize(context):
    context.i = -1  # minute counter
    context.exchange = list(context.exchanges.values())[0].name.lower()
    context.quote_currency = list(context.exchanges.values())[0].quote_currency.lower()


def handle_data(context, data):
    context.i += 1
    lookback_days = 7  # 7 days

    # current date & time in each iteration formatted into a string
    now = data.current_dt
    date, time = now.strftime('%Y-%m-%d %H:%M:%S').split(' ')
    lookback_date = now - timedelta(days=lookback_days)
    # keep only the date as a string, discard the time
    lookback_date = lookback_date.strftime('%Y-%m-%d %H:%M:%S').split(' ')[0]

    one_day_in_minutes = 1440  # 60 * 24 assumes data_frequency='minute'
    # update universe everyday at midnight
    if not context.i % one_day_in_minutes:
        context.universe = universe(context, lookback_date, date)

    # get data every 30 minutes
    minutes = 30

    # get lookback_days of history data: that is 'lookback' number of bins
    lookback = int(one_day_in_minutes / minutes * lookback_days)
    if not context.i % minutes and context.universe:
        # we iterate for every pair in the current universe
        for coin in context.coins:
            pair = str(coin.symbol)

            # Get 30 minute interval OHLCV data. This is the standard data
            # required for candlestick or indicators/signals. Return Pandas
            # DataFrames. 30T means 30-minute re-sampling of one minute data.
            # Adjust it to your desired time interval as needed.
            opened = fill(data.history(coin,
                                       'open',
                                       bar_count=lookback,
                                       frequency='30T')).values
            high = fill(data.history(coin,
                                     'high',
                                     bar_count=lookback,
                                     frequency='30T')).values
            low = fill(data.history(coin,
                                    'low',
                                    bar_count=lookback,
                                    frequency='30T')).values
            close = fill(data.history(coin,
                                      'price',
                                      bar_count=lookback,
                                      frequency='30T')).values
            volume = fill(data.history(coin,
                                       'volume',
                                       bar_count=lookback,
                                       frequency='30T')).values

            # close[-1] is the last value in the set, which is the equivalent
            # to current price (as in the most recent value)
            # displays the minute price for each pair every 30 minutes
            print('{now}: {pair} -\tO:{o},\tH:{h},\tL:{c},\tC{c},'
                  '\tV:{v}'.format(
                    now=now,
                    pair=pair,
                    o=opened[-1],
                    h=high[-1],
                    l=low[-1],
                    c=close[-1],
                    v=volume[-1],
                  ))

            # -------------------------------------------------------------
            # --------------- Insert Your Strategy Here -------------------
            # -------------------------------------------------------------


def analyze(context=None, results=None):
    pass


# Get the universe for a given exchange and a given quote_currency market
# Example: Poloniex BTC Market
def universe(context, lookback_date, current_date):
    # get all the pairs for the given exchange
    json_symbols = get_exchange_symbols(context.exchange)
    # convert into a DataFrame for easier processing
    df = pd.DataFrame.from_dict(json_symbols).transpose().astype(str)
    df['quote_currency'] = df.apply(lambda row: row.symbol.split('_')[1],
                                   axis=1)
    df['base_currency'] = df.apply(lambda row: row.symbol.split('_')[0],
                                     axis=1)

    # Filter all the pairs to get only the ones for a given quote_currency
    df = df[df['quote_currency'] == context.quote_currency]

    # Filter all pairs to ensure that pair existed in the current date range
    df = df[df.start_date < lookback_date]
    df = df[df.end_daily >= current_date]
    context.coins = symbols(*df.symbol)  # convert all the pairs to symbols

    return df.symbol.tolist()


# Replace all NA, NAN or infinite values with its nearest value
def fill(series):
    if isinstance(series, pd.Series):
        return series.replace([np.inf, -np.inf], np.nan).ffill().bfill()
    elif isinstance(series, np.ndarray):
        return pd.Series(series).replace(
                     [np.inf, -np.inf], np.nan
                    ).ffill().bfill().values
    else:
        return series


if __name__ == '__main__':
    start_date = pd.to_datetime('2017-11-10', utc=True)
    end_date = pd.to_datetime('2017-11-13', utc=True)

    performance = run_algorithm(start=start_date, end=end_date,
                                capital_base=100.0,  # amount of quote_currency
                                initialize=initialize,
                                handle_data=handle_data,
                                analyze=analyze,
                                exchange_name='poloniex',
                                data_frequency='minute',
                                quote_currency='btc',
                                live=False,
                                live_graph=False,
                                algo_namespace='simple_universe')
