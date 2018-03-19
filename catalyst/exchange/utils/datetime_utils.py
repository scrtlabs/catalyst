import calendar
import math
import re
from datetime import datetime, timedelta, date

import pandas as pd
import pytz

from catalyst.exchange.exchange_errors import InvalidHistoryFrequencyError, \
    InvalidHistoryFrequencyAlias


def get_date_from_ms(ms):
    """
    The date from the number of miliseconds from the epoch.

    Parameters
    ----------
    ms: int

    Returns
    -------
    datetime

    """
    return datetime.fromtimestamp(ms / 1000.0)


def get_seconds_from_date(date):
    """
    The number of seconds from the epoch.

    Parameters
    ----------
    date: datetime

    Returns
    -------
    int

    """
    epoch = datetime.utcfromtimestamp(0)
    epoch = epoch.replace(tzinfo=pytz.UTC)

    return int((date - epoch).total_seconds())


def get_delta(periods, data_frequency):
    """
    Get a time delta based on the specified data frequency.

    Parameters
    ----------
    periods: int
    data_frequency: str

    Returns
    -------
    timedelta

    """
    return timedelta(minutes=periods) \
        if data_frequency == 'minute' else timedelta(days=periods)


def get_periods_range(freq, start_dt=None, end_dt=None, periods=None):
    """
    Get a date range for the specified parameters.

    Parameters
    ----------
    start_dt: datetime
    end_dt: datetime
    freq: str

    Returns
    -------
    DateTimeIndex

    """
    if freq == 'minute':
        freq = 'T'

    elif freq == 'daily':
        freq = 'D'

    if start_dt is not None and end_dt is not None and periods is None:

        return pd.date_range(start_dt, end_dt, freq=freq)

    elif periods is not None and (start_dt is not None or end_dt is not None):
        _, unit_periods, unit, _ = get_frequency(freq)
        adj_periods = periods * unit_periods

        # TODO: standardize time aliases to avoid any mapping
        unit = 'd' if unit == 'D' else 'h' if unit == 'H' else 'm'
        delta = pd.Timedelta(adj_periods, unit)

        if start_dt is not None:
            return pd.date_range(
                start=start_dt,
                end=start_dt + delta,
                freq=freq,
                closed='left',
            )

        else:
            return pd.date_range(
                start=end_dt - delta,
                end=end_dt,
                freq=freq,
            )

    else:
        raise ValueError(
            'Choose only two parameters between start_dt, end_dt '
            'and periods.'
        )


def get_periods(start_dt, end_dt, freq):
    """
    The number of periods in the specified range.

    Parameters
    ----------
    start_dt: datetime
    end_dt: datetime
    freq: str

    Returns
    -------
    int

    """
    return len(get_periods_range(start_dt=start_dt, end_dt=end_dt, freq=freq))


def get_start_dt(end_dt, bar_count, data_frequency, include_first=True):
    """
    The start date based on specified end date and data frequency.

    Parameters
    ----------
    end_dt: datetime
    bar_count: int
    data_frequency: str
    include_first

    Returns
    -------
    datetime

    """
    periods = bar_count
    if periods > 1:
        delta = get_delta(periods, data_frequency)
        start_dt = end_dt - delta

        if not include_first:
            start_dt += get_delta(1, data_frequency)
    else:
        start_dt = end_dt

    return start_dt


def get_period_label(dt, data_frequency):
    """
    The period label for the specified date and frequency.

    Parameters
    ----------
    dt: datetime
    data_frequency: str

    Returns
    -------
    str

    """
    if data_frequency == 'minute':
        return '{}-{:02d}'.format(dt.year, dt.month)
    else:
        return '{}'.format(dt.year)


def get_month_start_end(dt, first_day=None, last_day=None):
    """
    The first and last day of the month for the specified date.

    Parameters
    ----------
    dt: datetime
    first_day: datetime
    last_day: datetime

    Returns
    -------
    datetime, datetime

    """
    month_range = calendar.monthrange(dt.year, dt.month)

    if first_day:
        month_start = first_day
    else:
        month_start = pd.to_datetime(datetime(
            dt.year, dt.month, 1, 0, 0, 0, 0
        ), utc=True)

    if last_day:
        month_end = last_day
    else:
        month_end = pd.to_datetime(datetime(
            dt.year, dt.month, month_range[1], 23, 59, 0, 0
        ), utc=True)

        if month_end > pd.Timestamp.utcnow():
            month_end = pd.Timestamp.utcnow().floor('1D')

    return month_start, month_end


def get_year_start_end(dt, first_day=None, last_day=None):
    """
    The first and last day of the year for the specified date.

    Parameters
    ----------

    dt: datetime
    first_day: datetime
    last_day: datetime

    Returns
    -------
    datetime, datetime

    """
    year_start = first_day if first_day \
        else pd.to_datetime(date(dt.year, 1, 1), utc=True)
    year_end = last_day if last_day \
        else pd.to_datetime(date(dt.year, 12, 31), utc=True)

    if year_end > pd.Timestamp.utcnow():
        year_end = pd.Timestamp.utcnow().floor('1D')

    return year_start, year_end


def get_frequency(freq, data_frequency=None, supported_freqs=['D', 'H', 'T']):
    """
    Takes an arbitrary candle size (e.g. 15T) and converts to the lowest
    common denominator supported by the data bundles (e.g. 1T). The data
    bundles only support 1T and 1D frequencies. If another frequency
    is requested, Catalyst must request the underlying data and resample.

    Notes
    -----
    We're trying to use Pandas convention for frequency aliases.

    Parameters
    ----------
    freq: str
    data_frequency: str

    Returns
    -------
    str, int, str, str

    """
    if data_frequency is None:
        data_frequency = 'daily' if freq.upper().endswith('D') else 'minute'

    if freq == 'minute':
        unit = 'T'
        candle_size = 1

    elif freq == 'daily':
        unit = 'D'
        candle_size = 1

    else:
        freq_match = re.match(r'([0-9].*)?(m|M|d|D|h|H|T)', freq, re.M | re.I)
        if freq_match:
            candle_size = int(freq_match.group(1)) if freq_match.group(1) \
                else 1
            unit = freq_match.group(2)

        else:
            raise InvalidHistoryFrequencyError(frequency=freq)

    # TODO: some exchanges support H and W frequencies but not bundles
    # Find a way to pass-through these parameters to exchanges
    # but resample from minute or daily in backtest mode
    # see catalyst/exchange/ccxt/ccxt_exchange.py:242 for mapping between
    # Pandas offet aliases (used by Catalyst) and the CCXT timeframes
    if unit.lower() == 'd':
        unit = 'D'
        alias = '{}D'.format(candle_size)

        if data_frequency == 'minute':
            data_frequency = 'daily'

    elif unit.lower() == 'm' or unit == 'T':
        unit = 'T'
        alias = '{}T'.format(candle_size)
        data_frequency = 'minute'

    elif unit.lower() == 'h':
        data_frequency = 'minute'

        if 'H' in supported_freqs:
            unit = 'H'
            alias = '{}H'.format(candle_size)
        else:
            candle_size = candle_size * 60
            alias = '{}T'.format(candle_size)

    else:
        raise InvalidHistoryFrequencyAlias(freq=freq)

    return alias, candle_size, unit, data_frequency


def from_ms_timestamp(ms):
    return pd.to_datetime(ms, unit='ms', utc=True)


def get_epoch():
    return pd.to_datetime('1970-1-1', utc=True)


def get_candles_number_from_minutes(unit, candle_size, minutes):
    """
    Get the number of bars needed for the given time interval
    in minutes.

    Notes
    -----
    Supports only "T", "D" and "H" units

    Parameters
    ----------
    unit: str
    candle_size : int
    minutes: int

    Returns
    -------
    int

    """
    if unit == "T":
        res = (float(minutes) / candle_size)
    elif unit == "H":
        res = (minutes / 60.0) / candle_size
    else:  # unit == "D"
        res = (minutes / 1440.0) / candle_size

    return int(math.ceil(res))
