import random
import shutil
import tempfile

import pandas as pd
from nose.tools import assert_equals

from catalyst.exchange.exchange_bcolz import BcolzExchangeBarWriter, \
    BcolzExchangeBarReader
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.utils.bundle_utils import get_df_from_arrays


class TestBcolzWriter(object):
    @classmethod
    def setup_class(cls):
        cls.columns = ['open', 'high', 'low', 'close', 'volume']

    def setUp(self):
        self.root_dir = tempfile.mkdtemp()  # Create a temporary directory

    def tearDown(self):
        shutil.rmtree(self.root_dir)  # Remove the directory after the test

    def generate_df(self, exchange_name, freq, start, end):
        bundle = ExchangeBundle(exchange_name)
        index = bundle.get_calendar_periods_range(start, end, freq)
        df = pd.DataFrame(index=index, columns=self.columns)
        df.fillna(random.random(), inplace=True)
        return df

    def test_bcolz_write_daily_past(self):
        start = pd.to_datetime('2016-01-01')
        end = pd.to_datetime('2016-12-31')
        freq = 'daily'

        df = self.generate_df('bitfinex', freq, start, end)

        writer = BcolzExchangeBarWriter(
            rootdir=self.root_dir,
            start_session=start,
            end_session=end,
            data_frequency=freq,
            write_metadata=True)

        data = []
        data.append((1, df))
        writer.write(data)
        pass

    def test_bcolz_write_daily_present(self):
        start = pd.to_datetime('2017-01-01')
        end = pd.to_datetime('today')
        freq = 'daily'

        df = self.generate_df('bitfinex', freq, start, end)

        writer = BcolzExchangeBarWriter(
            rootdir=self.root_dir,
            start_session=start,
            end_session=end,
            data_frequency=freq,
            write_metadata=True)

        data = []
        data.append((1, df))
        writer.write(data)
        pass

    def test_bcolz_write_minute_past(self):
        start = pd.to_datetime('2015-04-01 00:00')
        end = pd.to_datetime('2015-04-30 23:59')
        freq = 'minute'

        df = self.generate_df('bitfinex', freq, start, end)

        writer = BcolzExchangeBarWriter(
            rootdir=self.root_dir,
            start_session=start,
            end_session=end,
            data_frequency=freq,
            write_metadata=True)

        data = []
        data.append((1, df))
        writer.write(data)

        pass

    def test_bcolz_write_minute_present(self):
        start = pd.to_datetime('2017-10-01 00:00')
        end = pd.to_datetime('today')
        freq = 'minute'

        df = self.generate_df('bitfinex', freq, start, end)

        writer = BcolzExchangeBarWriter(
            rootdir=self.root_dir,
            start_session=start,
            end_session=end,
            data_frequency=freq,
            write_metadata=True)

        data = []
        data.append((1, df))
        writer.write(data)
        pass

    def bcolz_exchange_daily_write_read(self, exchange_name):
        start = pd.to_datetime('2017-10-01 00:00')
        end = pd.to_datetime('today')
        freq = 'daily'

        bundle = ExchangeBundle(exchange_name)

        df = self.generate_df(exchange_name, freq, start, end)

        print(df.index[0], df.index[-1])

        writer = BcolzExchangeBarWriter(
            rootdir=self.root_dir,
            start_session=df.index[0],
            end_session=df.index[-1],
            data_frequency=freq,
            write_metadata=True)

        data = []
        data.append((1, df))
        writer.write(data)

        reader = BcolzExchangeBarReader(rootdir=self.root_dir,
                                        data_frequency=freq)

        arrays = reader.load_raw_arrays(self.columns, start, end, [1, ])

        periods = bundle.get_calendar_periods_range(
            start, end, freq
        )

        dx = get_df_from_arrays(arrays, periods)

        assert_equals(df.equals(dx), True)
        pass

    def _test_bcolz_bitfinex_daily_write_read(self):
        self.bcolz_exchange_daily_write_read('bitfinex')

    def _test_bcolz_poloniex_daily_write_read(self):
        self.bcolz_exchange_daily_write_read('poloniex')
