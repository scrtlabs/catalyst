from time import sleep

import pandas as pd
from catalyst.constants import LOG_LEVEL
from catalyst.exchange.utils.stats_utils import prepare_stats
from catalyst.gens.sim_engine import (
    BAR,
    SESSION_START,
    SESSION_END,
)
from logbook import Logger

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

    def __init__(self, sessions, context, callback=None,
                 time_skew=pd.Timedelta('0s'), start=None, end=None):

        self.sessions = sessions
        self.time_skew = time_skew
        self._last_emit = None
        self._before_trading_start_bar_yielded = True
        self.context = context
        self.callback = callback
        self.start = start
        self.end = end

    def __iter__(self):
        from matplotlib import pyplot as plt

        self.handle_late_start()
        yield pd.Timestamp.utcnow(), SESSION_START

        while True:
            current_time = pd.Timestamp.utcnow()
            current_minute = current_time.floor('1T')

            if self.end is not None and current_minute >= self.end:
                break
            if self._last_emit is None or current_minute > self._last_emit:
                log.debug('emitting minutely bar: {}'.format(current_minute))

                self._last_emit = current_minute
                yield current_minute, BAR

                recorded_cols = list(self.context.recorded_vars.keys())
                df, _ = prepare_stats(
                    self.context.frame_stats, recorded_cols=recorded_cols
                )
                self.callback(self.context, df)

            else:
                # I can't use the "animate" reactive approach here because
                # I need to yield from the main loop.

                # Workaround: https://stackoverflow.com/a/33050617/814633
                plt.pause(1)

        yield current_minute, SESSION_END

    def handle_late_start(self):
        if self.start:
            time_diff = (self.start - pd.Timestamp.utcnow())
            log.info(
                'The algorithm is waiting for the specified '
                'start date: {}'.format(self.start))
            sleep(time_diff.seconds)

            while pd.Timestamp.utcnow() < self.start:
                pass
