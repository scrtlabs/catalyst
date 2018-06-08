import copy
import csv
import json
import numbers
import os
import time

import numpy as np
import pandas as pd
from catalyst.assets._assets import TradingPair
from catalyst.exchange.utils.exchange_utils import get_algo_folder
from catalyst.utils.paths import data_root, ensure_directory
from operator import itemgetter

s3_conn = []
mailgun = []


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


def set_position_row(row, asset, asset_values=list()):
    """
    Apply the position data as individual columns.

    Parameters
    ----------
    row: dict[str, Object]
    asset: TradingPair
    asset_values: list[str]
        If a recorded_col contains a tuple which first value is an asset
        matching a position, its value will be displayed with the
        position and not in the index.

    Returns
    -------

    """
    asset_cols = ['symbol']
    row['symbol'] = asset.symbol

    position = next((p for p in row['positions'] if p['sid'] == asset), None)

    columns = ['amount', 'cost_basis', 'last_sale_price']
    for column in columns:
        if position is not None:
            row[column] = position[column]

        else:
            row[column] = 0

        asset_cols.append(column)

    values = asset_values[asset] if asset in asset_values else list()
    for column in values:
        row[column] = values[column]

        asset_cols.append(column)

    return asset_cols


def prepare_stats(stats, recorded_cols=list()):
    """
    Prepare the stats DataFrame for user-friendly output.

    Parameters
    ----------
    stats: list[Object]
    recorded_cols: list[str]

    Returns
    -------

    """
    asset_cols = list()

    stats = copy.deepcopy(stats)
    # Using a copy since we are adding rows inside the loop.
    for row_index, row_data in enumerate(list(stats)):
        assets = [p['sid'] for p in row_data['positions']]

        asset_values = dict()
        if recorded_cols is not None:
            for column in recorded_cols[:]:
                value = row_data[column]
                if isinstance(value, pd.Series):
                    value = value.to_dict()

                if type(value) is dict:
                    for asset in value:
                        if not isinstance(asset, TradingPair):
                            break

                        if asset not in assets:
                            assets.append(asset)

                        if asset not in asset_values:
                            asset_values[asset] = dict()

                        asset_values[asset][column] = value[asset]

        if len(assets) == 1:
            row = stats[row_index]
            asset_cols = set_position_row(row, assets[0], asset_values)

        elif len(assets) > 1:
            for asset_index, asset in enumerate(assets):
                if asset_index > 0:
                    row = copy.deepcopy(row_data)
                    stats.append(row)

                else:
                    row = stats[row_index]

                asset_cols = set_position_row(row, assets[asset_index],
                                              asset_values)

    df = pd.DataFrame(stats)
    df['orders'] = df['orders'].apply(lambda orders: len(orders))
    df['transactions'] = df['transactions'].apply(
        lambda transactions: len(transactions)
    )
    index_cols = [
        'period_close', 'starting_cash', 'ending_cash', 'portfolio_value',
        'pnl', 'long_exposure', 'short_exposure', 'orders', 'transactions',
    ]

    # Removing the asset specific entries
    if recorded_cols is not None:
        recorded_cols = [x for x in recorded_cols if x not in asset_cols]
        for column in recorded_cols:
            index_cols.append(column)

    if asset_cols:
        columns = asset_cols
        df.set_index(index_cols, drop=True, inplace=True)

    else:
        columns = index_cols
        columns.remove('period_close')
        df.set_index('period_close', drop=False, inplace=True)

    df.dropna(axis=1, how='all', inplace=True)
    df.sort_index(axis=0, level=0, inplace=True)

    return df, columns


def set_print_settings():
    pd.set_option('display.expand_frame_repr', False)
    pd.set_option('precision', 8)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_colwidth', 1000)


def get_pretty_stats(stats, recorded_cols=None, num_rows=10, show_tail=True):
    """
    Format and print the last few rows of a statistics DataFrame.
    See the pyfolio project for the data structure.

    Parameters
    ----------
    stats: list[Object]
        An array of statistics for the period.

    num_rows: int
        The number of rows to display on the screen.

    Returns
    -------
    str

    """
    if isinstance(stats, pd.DataFrame):
        stats = list(stats.T.to_dict().values())
        stats.sort(key=itemgetter('period_close'))

    if len(stats) > num_rows:
        display_stats = stats[-num_rows:] if show_tail else stats[0:num_rows]
    else:
        display_stats = stats

    df, columns = prepare_stats(
        display_stats, recorded_cols=recorded_cols
    )
    set_print_settings()
    return df.to_string(columns=columns)


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
        # encoding='utf-8',
        quoting=csv.QUOTE_NONNUMERIC
    ).encode()


def stats_to_s3(uri, stats, algo_namespace, recorded_cols=None,
                folder='catalyst/stats', bytes_to_write=None):
    """
    Uploads the performance stats to a S3 bucket.

    Parameters
    ----------
    uri: str
    stats: list[Object]
    algo_namespace: str
    recorded_cols: list[str]
    folder: str
    bytes_to_write: str
        Option to reuse bytes instead of re-computing the csv

    Returns
    -------

    """
    if not s3_conn:
        import boto3
        s3_conn.append(boto3.resource('s3'))

    s3 = s3_conn[0]

    if bytes_to_write is None:
        bytes_to_write = get_csv_stats(stats, recorded_cols=recorded_cols)

    now = pd.Timestamp.utcnow()
    timestr = now.strftime('%Y%m%d')
    pid = os.getpid()

    parts = uri.split('//')
    path = '{folder}/{algo}/{time}-{algo}-{pid}.csv'.format(
        folder=folder,
        algo=algo_namespace,
        time=timestr,
        pid=pid,
    )
    obj = s3.Object(parts[1], path)
    obj.put(Body=bytes_to_write)


def email_error(algo_name, dt, e, environ=None):
    import requests
    import traceback

    if not mailgun:
        root = data_root(environ)
        filename = os.path.join(root, 'mailgun.json')
        if not os.path.exists(filename):
            raise ValueError(
                'mailgun.json not found in the catalyst data folder'
            )

        with open(filename) as data_file:
            mailgun.append(json.load(data_file))

    mg = mailgun[0]

    return requests.post(
        mg['url'],
        auth=("api", mg['api']),
        data={
            "from": mg['from'],
            "to": mg['to'],
            "subject": 'Error: {}'.format(algo_name),
            "text": '{}\n\n{}\n{}'.format(
                dt, e, traceback.format_exc()
            )})


def stats_to_algo_folder(stats, algo_namespace,
                         folder_name, recorded_cols=None):
    """
    Saves the performance stats to the algo local folder.

    Parameters
    ----------
    stats: list[Object]
    algo_namespace: str
    folder_name: str
    recorded_cols: list[str]

    Returns
    -------
    str

    """
    bytes_to_write = get_csv_stats(stats, recorded_cols=recorded_cols)

    timestr = time.strftime('%Y%m%d')
    folder = get_algo_folder(algo_namespace)

    stats_folder = os.path.join(folder, folder_name)
    ensure_directory(stats_folder)

    filename = os.path.join(stats_folder, '{}.csv'.format(timestr))

    with open(filename, 'wb') as handle:
        handle.write(bytes_to_write)

    return bytes_to_write


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


def extract_orders(perf):
    order_list = perf.orders.values
    all_orders = [t for sublist in order_list for t in sublist]
    all_orders.sort(key=lambda o: o['dt'])

    orders = pd.DataFrame(all_orders)
    if not orders.empty:
        orders.set_index('dt', inplace=True, drop=True)
    return orders


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
