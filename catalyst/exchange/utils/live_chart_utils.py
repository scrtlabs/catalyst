import matplotlib.dates as mdates
import pandas as pd

from catalyst.exchange.exchange_errors import \
    MismatchingQuoteCurrenciesExchanges

fmt = mdates.DateFormatter('%Y-%m-%d %H:%M')


def format_ax(ax):
    """
    Trying to assign reasonable parameters to the time axis.

    Parameters
    ----------
    ax:

    """
    # TODO: room for improvement
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.xaxis.set_major_formatter(fmt)

    locator = mdates.HourLocator(interval=4)
    locator.MAXTICKS = 5000
    ax.xaxis.set_minor_locator(locator)

    datemin = pd.Timestamp.utcnow()
    ax.set_xlim(datemin)

    ax.grid(True)


def set_legend(ax):
    """
    Set legend on the chart.

    Parameters
    ----------
    ax

    """
    ax.legend(loc='upper left', ncol=1, fontsize=10, numpoints=1)


def draw_pnl(ax, df):
    """
    Draw p&l line on the chart.

    """
    ax.clear()
    ax.set_title('Performance')
    index = df.index.unique()
    dt = index.get_level_values(level=0)
    pnl = index.get_level_values(level=4)
    ax.plot(
        dt, pnl, '-',
        color='green',
        linewidth=1.0,
        label='Performance'
    )

    def perc(val):
        return '{:2f}'.format(val)

    ax.format_ydata = perc

    set_legend(ax)
    format_ax(ax)


def draw_custom_signals(ax, df):
    """
    Draw custom signals on the chart.

    """
    colors = ['blue', 'green', 'red', 'black', 'orange', 'yellow', 'pink']

    ax.clear()
    ax.set_title('Custom Signals')
    for index, column in enumerate(df.columns.values.tolist()):
        ax.plot(df.index, df[column], '-',
                color=colors[index],
                linewidth=1.0,
                label=column
                )

    set_legend(ax)
    format_ax(ax)


def draw_exposure(ax, df, context):
    """
    Draw exposure line on the chart.

    """
    # TODO: list exchanges in graph
    quote_currency = None
    positions = []
    for exchange_name in context.exchanges:
        exchange = context.exchanges[exchange_name]

        if not quote_currency:
            quote_currency = exchange.quote_currency
        elif quote_currency != exchange.quote_currency:
            raise MismatchingQuoteCurrenciesExchanges(
                quote_currency=quote_currency,
                exchange_name=exchange.name,
                exchange_currency=exchange.quote_currency
            )

        positions += exchange.portfolio.positions

    ax.clear()
    ax.set_title('Exposure')
    ax.plot(df.index, df['quote_currency'], '-',
            color='green',
            linewidth=1.0,
            label='Base Currency: {}'.format(quote_currency.upper())
            )

    symbols = []
    for position in positions:
        symbols.append(position.symbol)

    ax.plot(df.index, df['long_exposure'], '-',
            color='blue',
            linewidth=1.0,
            label='Long Exposure: {}'.format(', '.join(symbols).upper()))

    set_legend(ax)
    format_ax(ax)
