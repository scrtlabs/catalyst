import numpy as np

from catalyst import get_calendar
from catalyst.data.minute_bars import BcolzMinuteBarReader, \
    BcolzMinuteBarWriter
from catalyst.exchange.bundle_utils import get_periods, get_periods_range


class BcolzExchangeBarWriter(BcolzMinuteBarWriter):
    def __init__(self, *args, **kwargs):
        self._data_frequency = kwargs.pop('data_frequency', None)
        kwargs.pop('minutes_per_day', None)
        kwargs.pop('calendar', None)

        end_session = kwargs.pop('end_session', None)
        if end_session is not None:
            end_session = end_session.floor('1d')

        minutes_per_day = 1440 if self._data_frequency == 'minute' else 1
        default_ohlc_ratio = kwargs.pop('default_ohlc_ratio', 1000000)
        calendar = get_calendar('OPEN')

        super(BcolzExchangeBarWriter, self) \
            .__init__(*args, **dict(kwargs,
                                    minutes_per_day=minutes_per_day,
                                    default_ohlc_ratio=default_ohlc_ratio,
                                    calendar=calendar,
                                    end_session=end_session
                                    ))


class BcolzExchangeBarReader(BcolzMinuteBarReader):
    def __init__(self, *args, **kwargs):
        self._data_frequency = kwargs.pop('data_frequency', None)

        super(BcolzExchangeBarReader, self).__init__(*args, **kwargs)

    @property
    def data_frequency(self):
        return self._data_frequency

    def load_raw_arrays(self, fields, start_dt, end_dt, sids):

        if self._data_frequency == 'minute':
            return super(BcolzExchangeBarReader, self) \
                .load_raw_arrays(fields, start_dt, end_dt, sids)

        else:
            return self._load_daily_raw_arrays(fields, start_dt, end_dt, sids)

    def _load_daily_raw_arrays(self, fields, start_dt, end_dt, sids):
        start_idx = self._find_position_of_minute(start_dt)
        end_idx = self._find_position_of_minute(end_dt)

        periods = get_periods_range(start_dt, end_dt, self.data_frequency)
        num_days = len(periods)
        shape = num_days, len(sids)

        if len(fields) == 1 and fields[0] == 'volume':
            fields.insert(0, 'close')

        mask = None
        data = []
        for field in fields:
            out = np.full(shape, np.nan)

            for i, sid in enumerate(sids):
                carray = self._open_minute_file(field, sid)
                a = carray[start_idx:end_idx + 1]

                if mask is None:
                    mask = a != 0

                out[:len(mask), i][mask] = (
                    a[mask] * self._ohlc_ratio_inverse_for_sid(sid)
                )

            data.append(out)

        return data
