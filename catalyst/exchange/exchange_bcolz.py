import numpy as np

from catalyst import get_calendar
from catalyst.data.minute_bars import BcolzMinuteBarReader, \
    BcolzMinuteBarWriter


class BcolzExchangeBarWriter(BcolzMinuteBarWriter):
    def __init__(self, *args, **kwargs):
        self._data_frequency = kwargs.pop('data_frequency', None)
        kwargs.pop('minutes_per_day', None)
        kwargs.pop('calendar', None)

        end_session = kwargs.pop('end_session', None)
        if end_session is not None:
            end_session = end_session.floor('1d')

        minutes_per_day = 1440 if self._data_frequency == 'minute' else 1
        default_ohlc_ratio = kwargs.pop('default_ohlc_ratio', 100000000)
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
        """
        Parameters
        ----------
        fields : list of str
           'open', 'high', 'low', 'close', or 'volume'
        start_dt: Timestamp
           Beginning of the window range.
        end_dt: Timestamp
           End of the window range.
        sids : list of int
           The asset identifiers in the window.

        Returns
        -------
        list of np.ndarray
            A list with an entry per field of ndarrays with shape
            (minutes in range, sids) with a dtype of float64, containing the
            values for the respective field over start and end dt range.
        """
        start_idx = self._find_position_of_minute(start_dt)
        end_idx = self._find_position_of_minute(end_dt)

        periods = self.calendar.minutes_in_range(start_dt, end_dt) \
            if self.data_frequency == 'minute' \
            else self.calendar.sessions_in_range(start_dt, end_dt)

        num_days = len(periods)
        shape = num_days, len(sids)

        all_fields = fields[:]
        if len(all_fields) == 1 and all_fields[0] == 'volume':
            all_fields.insert(0, 'close')

        mask = None
        data = []
        for field in all_fields:
            if field != 'volume':
                out = np.full(shape, np.nan)
            else:
                out = np.zeros(shape, dtype=np.float64)

            for i, sid in enumerate(sids):
                carray = self._open_minute_file(field, sid)
                a = carray[start_idx:end_idx + 1]

                if mask is None:
                    mask = a != 0

                inverse_ratio = self._ohlc_ratio_inverse_for_sid(sid)
                out[:len(mask), i][mask] = (
                    a[mask] * inverse_ratio
                )

            if field in fields:
                data.append(out)

        return data
