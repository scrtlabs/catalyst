import shutil
import tempfile
import pandas as pd

from catalyst import get_calendar
from catalyst.exchange.exchange_bcolz import BcolzExchangeBarWriter


class TestBcolzWriter(object):
    @classmethod
    def setup_class(cls):
        cls.columns = ['open', 'high', 'low', 'close', 'volume']

    def setUp(self):
        # Create a temporary directory
        self.root_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.root_dir)

    def test_bcolz_write_daily(self):
        start = pd.to_datetime('2015-01-01')
        end = pd.to_datetime('2015-12-31')
        freq = 'daily'

        calendar = get_calendar('OPEN')
        # index = pd.date_range(start=start, end=end, freq='D', name='date')
        index = calendar.sessions_in_range(start, end)
        df = pd.DataFrame(index=index, columns=self.columns)
        df.fillna(1, inplace=True)

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

    def test_bcolz_write_minute(self):
        index = pd.date_range(start=pd.to_datetime('2015-01-01'),
                              end=pd.to_datetime('2015-01-31'), freq='T',
                              name='date')
