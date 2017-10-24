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
    	self.root_dir = tempfile.mkdtemp()			# Create a temporary directory

    def tearDown(self):
    	shutil.rmtree(self.root_dir)				# Remove the directory after the test

    def test_bcolz_write_daily_past(self):
        start = pd.to_datetime('2015-01-01')
        end = pd.to_datetime('2015-12-31')
        freq = 'daily'

        calendar = get_calendar('OPEN')
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

    def test_bcolz_write_daily_present(self):
        start = pd.to_datetime('2017-01-01')
        end   = pd.to_datetime('today')
        freq  = 'daily'

        calendar = get_calendar('OPEN')
        index = calendar.sessions_in_range(start, end)
        df = pd.DataFrame(index=index, columns=self.columns)
        df.fillna(1, inplace=True)

        writer = BcolzExchangeBarWriter(
        				rootdir  = self.root_dir,
        				start_session   = start,
                        end_session     = end,
                        data_frequency  = freq,
                        write_metadata  = True )

        data = []
        data.append((1,df))
        writer.write(data)
        pass

    def test_bcolz_write_minute_past(self):
        start = pd.to_datetime('2015-03-01')
        end   = pd.to_datetime('2015-03-31')
        freq  = 'minute'

        calendar = get_calendar('OPEN')
        index = calendar.sessions_in_range(start, end)
        df = pd.DataFrame(index=index, columns=self.columns)
        df.fillna(1, inplace=True)

        writer = BcolzExchangeBarWriter(
        				rootdir  = self.root_dir,
        				start_session   = start,
                        end_session     = end,
                        data_frequency  = freq,
                        write_metadata  = True )

        data = []
        data.append((1,df))
        writer.write(data)
        pass

    def test_bcolz_write_minute_present(self):
        start = pd.to_datetime('2017-10-01')
        end   = pd.to_datetime('today')
        freq  = 'minute'

        calendar = get_calendar('OPEN')
        index = calendar.sessions_in_range(start, end)
        df = pd.DataFrame(index=index, columns=self.columns)
        df.fillna(1, inplace=True)

        writer = BcolzExchangeBarWriter(
        				rootdir  = self.root_dir,
        				start_session   = start,
                        end_session     = end,
                        data_frequency  = freq,
                        write_metadata  = True )

        data = []
        data.append((1,df))
        writer.write(data)
        pass

