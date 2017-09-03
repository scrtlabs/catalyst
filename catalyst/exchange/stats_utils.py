import pandas as pd


def get_pretty_stats(stats_df, num_rows=10):
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
