from datetime import time
from pytz import timezone

from .trading_calendar import TradingCalendar

from catalyst.utils.memoize import lazyval


class OpenExchangeCalendar(TradingCalendar):
    @property
    def name(self):
        return 'OPEN'

    @property
    def tz(self):
        return timezone('US/Eastern')

    @property
    def open_time(self):
        return time(0)

    @property
    def close_time(self):
        return time(23, 59)

    @lazyval
    def day(self):
        return 'D'
