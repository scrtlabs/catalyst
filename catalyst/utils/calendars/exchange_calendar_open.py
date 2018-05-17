from datetime import time
from pytz import timezone

from pandas import Timestamp
from pandas.tseries.offsets import DateOffset

from catalyst.utils.memoize import lazyval

from .trading_calendar import TradingCalendar


class OpenExchangeCalendar(TradingCalendar):
    @property
    def name(self):
        return 'OPEN'

    @property
    def tz(self):
        return timezone('UTC')

    @property
    def open_time(self):
        return time(0)

    @property
    def close_time(self):
        return time(23, 59)

    @lazyval
    def day(self):
        return DateOffset(days=1)

    def __init__(self, *args, **kwargs):
        super(OpenExchangeCalendar, self).__init__(
            start=Timestamp('2015-3-1', tz='UTC'), **kwargs)
