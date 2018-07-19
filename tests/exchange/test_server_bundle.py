"""
import importlib
import os

import matplotlib
import matplotlib.pyplot as plt
# from matplotlib.finance import volume_overlay
import matplotlib.ticker as ticker
import pandas as pd
from matplotlib.finance import candlestick2_ohlc

from catalyst.exchange.exchange_bcolz import BcolzExchangeBarReader
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.utils.bundle_utils import get_df_from_arrays, \
    get_bcolz_chunk
from catalyst.exchange.utils.factory import get_exchange


class ValidateChunks(object):
    def __init__(self):
        self.columns = ['open', 'high', 'low', 'close', 'volume']

    def chunk_to_df(self, exchange_name, symbol, data_frequency, period):

        exchange = get_exchange(exchange_name)
        asset = exchange.get_asset(symbol)

        filename = get_bcolz_chunk(
            exchange_name=exchange_name,
            symbol=symbol,
            data_frequency=data_frequency,
            period=period
        )

        reader = BcolzExchangeBarReader(rootdir=filename,
                                        data_frequency=data_frequency)

        # metadata = BcolzMinuteBarMetadata.read(filename)

        start = reader.first_trading_day
        end = reader.last_available_dt

        if data_frequency == 'daily':
            end = end - pd.Timedelta(hours=23, minutes=59)

        print(start, end, data_frequency)

        arrays = reader.load_raw_arrays(self.columns, start, end,
                                        [asset.sid, ])

        bundle = ExchangeBundle(exchange_name)

        periods = bundle.get_calendar_periods_range(
            start, end, data_frequency
        )

        return get_df_from_arrays(arrays, periods)

    def plot_ohlcv(self, df):

        fig, ax = plt.subplots()

        # Plot the candlestick
        candlestick2_ohlc(ax, df['open'], df['high'], df['low'], df['close'],
                          width=1, colorup='g', colordown='r', alpha=0.5)

        # shift y-limits of the candlestick plot so that there is space
        # at the bottom for the volume bar chart
        pad = 0.25
        yl = ax.get_ylim()
        ax.set_ylim(yl[0] - (yl[1] - yl[0]) * pad, yl[1])

        # Add a seconds axis for the volume overlay
        ax2 = ax.twinx()

        ax2.set_position(
            matplotlib.transforms.Bbox([[0.125, 0.1], [0.9, 0.26]]))

        # Plot the volume overlay
        # bc = volume_overlay(ax2, df['open'], df['close'], df['volume'],
        #                     colorup='g', alpha=0.5, width=1)

        ax.xaxis.set_major_locator(ticker.MaxNLocator(6))

        def mydate(x, pos):
            try:
                return df.index[int(x)]
            except IndexError:
                return ''

        ax.xaxis.set_major_formatter(ticker.FuncFormatter(mydate))
        plt.margins(0)
        plt.show()

    def plot(self, filename):
        df = self.chunk_to_df(filename)
        self.plot_ohlcv(df)

    def to_csv(self, filename):
        df = self.chunk_to_df(filename)
        df.to_csv(os.path.basename(filename).split('.')[0] + '.csv')


v = ValidateChunks()

df = v.chunk_to_df(
    exchange_name='bitfinex',
    symbol='eth_btc',
    data_frequency='daily',
    period='2016'
)
print(df.tail())
v.plot_ohlcv(df)
# v.plot(
#     ex
# )
"""
