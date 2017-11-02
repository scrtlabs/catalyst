import pandas as pd
from catalyst.gens.sim_engine import (
    BAR,
    SESSION_START
)
from logbook import Logger

from catalyst.constants import LOG_LEVEL
from catalyst.exchange.exchange_errors import \
    MismatchingBaseCurrenciesExchanges

log = Logger('LiveGraphClock', level=LOG_LEVEL)


class LiveGraphClock(object):
    """Realtime clock for live trading.

    This class is a drop-in replacement for
    :class:`zipline.gens.sim_engine.MinuteSimulationClock`.

    This mixes the clock with a live graph.

    Notes
    -----
    This seemingly awkward approach allows us to run the program using a single
    thread. This is important because Matplotlib does not play nice with
    multi-threaded environments. Zipline probably does not either.


    Matplotlib has a pause() method which is a wrapper around time.sleep()
    used in the SimpleClock. The key difference is that users
    can still interact with the chart during the pause cycles. This is
    what enables us to keep a single thread. This is also why we are not using
    the 'animate' callback of Matplotlib. We need to direct access to the
    __iter__ method in order to yield events to Zipline.

    The :param:`time_skew` parameter represents the time difference between
    the exchange and the live trading machine's clock. It's not used currently.
    """

    def __init__(self, sessions, context, time_skew=pd.Timedelta('0s')):

        global mdates, plt  # TODO: Could be cleaner
        import matplotlib.dates as mdates
        from matplotlib import pyplot as plt
        from matplotlib import style

        self.sessions = sessions
        self.time_skew = time_skew
        self._last_emit = None
        self._before_trading_start_bar_yielded = True
        self.context = context
        self.fmt = mdates.DateFormatter('%Y-%m-%d %H:%M')

        style.use('dark_background')

        fig = plt.figure()
        fig.canvas.set_window_title('Enigma Catalyst: {}'.format(
            self.context.algo_namespace))

        self.ax_pnl = fig.add_subplot(311)

        self.ax_custom_signals = fig.add_subplot(312, sharex=self.ax_pnl)

        self.ax_exposure = fig.add_subplot(313, sharex=self.ax_pnl)

        if len(context.minute_stats) > 0:
            self.draw_pnl()
            self.draw_custom_signals()
            self.draw_exposure()

        # rotates and right aligns the x labels, and moves the bottom of the
        # axes up to make room for them
        fig.autofmt_xdate()
        fig.subplots_adjust(hspace=0.5)

        plt.tight_layout()
        plt.ion()
        plt.show()

    def format_ax(self, ax):
        """
        Trying to assign reasonable parameters to the time axis.

        Parameters
        ----------
        ax:

        """
        # TODO: room for improvement
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax.xaxis.set_major_formatter(self.fmt)

        locator = mdates.HourLocator(interval=4)
        locator.MAXTICKS = 5000
        ax.xaxis.set_minor_locator(locator)

        datemin = pd.Timestamp.utcnow()
        ax.set_xlim(datemin)

        ax.grid(True)

    def set_legend(self, ax):
        """
        Set legend on the chart.

        Parameters
        ----------
        ax

        """
        ax.legend(loc='upper left', ncol=1, fontsize=10, numpoints=1)

    def draw_pnl(self):
        """
        Draw p&l line on the chart.

        """
        ax = self.ax_pnl
        df = self.context.pnl_stats

        ax.clear()
        ax.set_title('Performance')
        ax.plot(df.index, df['performance'], '-',
                color='green',
                linewidth=1.0,
                label='Performance'
                )

        def perc(val):
            return '{:2f}'.format(val)

        ax.format_ydata = perc

        self.set_legend(ax)
        self.format_ax(ax)

    def draw_custom_signals(self):
        """
        Draw custom signals on the chart.

        """
        ax = self.ax_custom_signals
        df = self.context.custom_signals_stats

        colors = ['blue', 'green', 'red', 'black', 'orange', 'yellow', 'pink']

        ax.clear()
        ax.set_title('Custom Signals')
        for index, column in enumerate(df.columns.values.tolist()):
            ax.plot(df.index, df[column], '-',
                    color=colors[index],
                    linewidth=1.0,
                    label=column
                    )

        self.set_legend(ax)
        self.format_ax(ax)

    def draw_exposure(self):
        """
        Draw exposure line on the chart.

        """
        ax = self.ax_exposure
        context = self.context
        df = context.exposure_stats

        # TODO: list exchanges in graph
        base_currency = None
        positions = []
        for exchange_name in context.exchanges:
            exchange = context.exchanges[exchange_name]

            if not base_currency:
                base_currency = exchange.base_currency
            elif base_currency != exchange.base_currency:
                raise MismatchingBaseCurrenciesExchanges(
                    base_currency=base_currency,
                    exchange_name=exchange.name,
                    exchange_currency=exchange.base_currency
                )

            positions += exchange.portfolio.positions

        ax.clear()
        ax.set_title('Exposure')
        ax.plot(df.index, df['base_currency'], '-',
                color='green',
                linewidth=1.0,
                label='Base Currency: {}'.format(base_currency.upper())
                )

        symbols = []
        for position in positions:
            symbols.append(position.symbol)

        ax.plot(df.index, df['long_exposure'], '-',
                color='blue',
                linewidth=1.0,
                label='Long Exposure: {}'.format(', '.join(symbols).upper()))

        self.set_legend(ax)
        self.format_ax(ax)

    def __iter__(self):
        yield pd.Timestamp.utcnow(), SESSION_START

        while True:
            current_time = pd.Timestamp.utcnow()
            current_minute = current_time.floor('1 min')

            if self._last_emit is None or current_minute > self._last_emit:
                log.debug('emitting minutely bar: {}'.format(current_minute))

                self._last_emit = current_minute
                yield current_minute, BAR

                try:
                    self.draw_pnl()
                    self.draw_custom_signals()
                    self.draw_exposure()

                    plt.draw()
                except Exception as e:
                    log.warn('Unable to update the graph: {}'.format(e))

            else:
                # I can't use the "animate" reactive approach here because
                # I need to yield from the main loop.

                # Workaround: https://stackoverflow.com/a/33050617/814633
                plt.pause(1)
