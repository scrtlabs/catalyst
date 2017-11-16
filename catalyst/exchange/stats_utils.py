import numbers

import numpy as np
import pandas as pd


def trend_direction(series):
    if series[-1] is np.nan or series[-1] is np.nan:
        return None

    if series[-1] > series[-2]:
        return 'up'
    else:
        return 'down'


def crossover(source, target):
    """
    The `x`-series is defined as having crossed over `y`-series if the value
    of `x` is greater than the value of `y` and the value of `x` was less than
    the value of `y` on the bar immediately preceding the current bar.

    Parameters
    ----------
    source: Series
    target: Series

    Returns
    -------
    bool

    """
    if isinstance(target, numbers.Number):
        if source[-1] is np.nan or source[-2] is np.nan \
                or target is np.nan:
            return False

        if source[-1] >= target > source[-2]:
            return True
        else:
            return False

    else:
        if source[-1] is np.nan or source[-2] is np.nan \
                or target[-1] is np.nan or target[-2] is np.nan:
            return False

        if source[-1] > target[-1] and source[-2] < target[-2]:
            return True
        else:
            return False


def crossunder(source, target):
    """
    The `x`-series is defined as having crossed under `y`-series if the value
    of `x` is less than the value of `y` and the value of `x` was greater than
    the value of `y` on the bar immediately preceding the current bar.

    Parameters
    ----------
    source: Series
    target: Series

    Returns
    -------
    bool

    """
    if isinstance(target, numbers.Number):
        if source[-1] is np.nan or source[-2] is np.nan \
                or target is np.nan:
            return False

        if source[-1] < target <= source[-2]:
            return True
        else:
            return False
    else:
        if source[-1] is np.nan or source[-2] is np.nan \
                or target[-1] is np.nan or target[-2] is np.nan:
            return False

        if source[-1] < target[-1] and source[-2] >= target[-2]:
            return True
        else:
            return False


def vwap(df):
    """
    Volume-weighted average price (VWAP) is a ratio generally used by
    institutional investors and mutual funds to make buys and sells so as not
    to disturb the market prices with large orders. It is the average share
    price of a stock weighted against its trading volume within a particular
    time frame, generally one day.

    Read more: Volume Weighted Average Price - VWAP
    https://www.investopedia.com/terms/v/vwap.asp#ixzz4xt922daE

    Parameters
    ----------
    df: pd.DataFrame

    Returns
    -------

    """
    if 'close' not in df.columns or 'volume' not in df.columns:
        raise ValueError('price data must include `volume` and `close`')

    vol_sum = np.nansum(df['volume'].values)

    try:
        ret = np.nansum(df['close'].values * df['volume'].values) / vol_sum
    except ZeroDivisionError:
        ret = np.nan

    return ret


def get_pretty_stats(stats_df, recorded_cols=None, num_rows=10):
    """
    Format and print the last few rows of a statistics DataFrame.
    See the pyfolio project for the data structure.

    Parameters
    ----------
    stats_df: DataFrame
    num_rows: int

    Returns
    -------
    str

    """
    stats_df.set_index('period_close', drop=True, inplace=True)
    stats_df.dropna(axis=1, how='all', inplace=True)

    pd.set_option('display.expand_frame_repr', False)
    pd.set_option('precision', 3)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_colwidth', 1000)

    columns = ['starting_cash', 'ending_cash', 'portfolio_value',
               'pnl', 'long_exposure', 'short_exposure', 'orders',
               'transactions', 'positions']

    if recorded_cols is not None:
        for column in recorded_cols:
            columns.append(column)

    def format_positions(positions):
        parts = []
        for position in positions:
            msg = '{amount:.2f}{market} cost basis {cost_basis:.4f}{base}'.format(
                amount=position['amount'],
                market=position['sid'].market_currency,
                cost_basis=position['cost_basis'],
                base=position['sid'].base_currency
            )
            parts.append(msg)
        return ', '.join(parts)

    formatters = {
        'orders': lambda orders: len(orders),
        'transactions': lambda transactions: len(transactions),
        'returns': lambda returns: "{0:.4f}".format(returns),
        'positions': format_positions
    }

    return stats_df.tail(num_rows).to_string(
        columns=columns,
        formatters=formatters
    )


def df_to_string(df):
    """
    Create a formatted str representation of the DataFrame.

    Parameters
    ----------
    df: DataFrame

    Returns
    -------
    str

    """
    pd.set_option('display.expand_frame_repr', False)
    pd.set_option('precision', 8)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_colwidth', 1000)

    return df.to_string()


def extract_transactions(perf):
    """
    Compute indexes for buy and sell transactions

    Parameters
    ----------
    perf: DataFrame
        The algo performance DataFrame.

    Returns
    -------
    DataFrame
        A DataFrame of transactions.

    """
    trans_list = perf.transactions.values
    all_trans = [t for sublist in trans_list for t in sublist]
    all_trans.sort(key=lambda t: t['dt'])

    transactions = pd.DataFrame(all_trans)
    if not transactions.empty:
        transactions.set_index('dt', inplace=True, drop=True)
    return transactions
