import pandas as pd
import numpy as np


def crossover(source, target):
    """
    The `x`-series is defined as having crossed over `y`-series if the value
    of `x` is greater than the value of `y` and the value of `x` was less than
    the value of `y` on the bar immediately preceding the current bar.

    :param source:
    :param target:
    :return:
    """
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
    :param source:
    :param target:
    :return:
    """
    if source[-1] is np.nan or source[-2] is np.nan \
            or target[-1] is np.nan or target[-2] is np.nan:
        return False

    if source[-1] < target[-1] and source[-2] > target[-2]:
        return True
    else:
        return False


def get_pretty_stats(stats_df, recorded_cols=None, num_rows=10):
    """
    Format and print the last few rows of a statistics DataFrame.
    See the pyfolio project for the data structure.

    :param stats_df:
    :param num_rows:
    :return:
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
    pd.set_option('display.expand_frame_repr', False)
    pd.set_option('precision', 8)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_colwidth', 1000)

    return df.to_string()
