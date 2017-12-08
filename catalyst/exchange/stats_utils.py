import numbers

import copy
import numpy as np
import pandas as pd
import boto3
import time

from catalyst.assets._assets import TradingPair

s3 = boto3.resource('s3')


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


def set_position_row(row, position_index, recorded_cols=None):
    """
    Apply the position data as individual columns.

    Parameters
    ----------
    row: dict[str, Object]
    position_index: int
    recorded_cols: list[str]
        If a recorded_col contains a tuple which first value is an asset
        matching a position, its value will be displayed with the
        position and not in the index.

    Returns
    -------

    """
    position = row['positions'][position_index]

    asset = position['sid']
    row['symbol'] = asset.symbol

    columns = ['amount', 'cost_basis', 'last_sale_price']
    for column in columns:
        row[column] = position[column]

    columns.insert(0, 'symbol')

    if recorded_cols is not None:
        for column in recorded_cols[:]:
            value = row[column]
            if type(value) in [list, tuple] and \
                    isinstance(value[0], TradingPair) and asset == value[0]:
                row[column] = value[1]

                columns.append(column)
                # Removing the asset specific entries
                recorded_cols.remove(column)

    return columns


def prepare_stats(stats, recorded_cols=None):
    """
    Prepare the stats DataFrame for user-friendly output.

    Parameters
    ----------
    stats: list[Object]
    recorded_cols: list[str]

    Returns
    -------

    """
    position_cols = None

    # Using a copy since we are adding rows inside the loop.
    for row_index, row_data in enumerate(list(stats)):
        if len(row_data['positions']) == 1:
            row = stats[row_index]
            columns = set_position_row(row, 0, recorded_cols)

        elif len(row_data['positions']) > 1:
            for pos_index, position in enumerate(row_data['positions']):
                if pos_index > 0:
                    row = row_data
                    stats.append(row)

                else:
                    row = stats[row_index]

                columns = set_position_row(row, pos_index, recorded_cols)

        else:
            break

        if position_cols is None:
            position_cols = columns

    df = pd.DataFrame(list(stats))

    index_cols = [
        'period_close', 'starting_cash', 'ending_cash', 'portfolio_value',
        'pnl', 'long_exposure', 'short_exposure', 'orders', 'transactions',
    ]
    if recorded_cols is not None:
        for column in recorded_cols:
            index_cols.append(column)

    df['orders'] = df['orders'].apply(lambda orders: len(orders))
    df['transactions'] = df['transactions'].apply(
        lambda transactions: len(transactions)
    )

    df.set_index(index_cols, drop=True, inplace=True)
    df.dropna(axis=1, how='all', inplace=True)

    return df, position_cols


def get_pretty_stats(stats, recorded_cols=None, num_rows=10):
    """
    Format and print the last few rows of a statistics DataFrame.
    See the pyfolio project for the data structure.

    Parameters
    ----------
    stats: list[Object]
    num_rows: int

    Returns
    -------
    str

    """
    df, columns = prepare_stats(stats, recorded_cols=recorded_cols)

    pd.set_option('display.expand_frame_repr', False)
    pd.set_option('precision', 3)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_colwidth', 1000)

    formatters = {
        'returns': lambda returns: "{0:.4f}".format(returns),
    }

    return df.tail(num_rows).to_string(
        columns=columns,
        formatters=formatters
    )


def get_csv_stats(stats, recorded_cols=None):
    """
    Create a CSV buffer from the stats DataFrame.

    Parameters
    ----------
    path: str
    stats: list[Object]
    recorded_cols: list[str]

    Returns
    -------

    """
    df, columns = prepare_stats(stats, recorded_cols=recorded_cols)

    return df.to_csv(
        None,
        columns=columns,
        encoding='utf-8',
    ).encode()


def stats_to_s3(uri, stats, algo_namespace, recorded_cols=None):
    bytes_to_write = get_csv_stats(stats, recorded_cols=recorded_cols)

    timestr = time.strftime('%Y%m%d')

    parts = uri.split('//')
    obj = s3.Object(parts[1], 'stats/{}-{}.csv'.format(
        timestr, algo_namespace
    ))
    obj.put(Body=bytes_to_write)


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
