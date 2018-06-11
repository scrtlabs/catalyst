#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from time import sleep

import pandas as pd
from catalyst.constants import LOG_LEVEL
from catalyst.gens.sim_engine import (
    BAR,
    SESSION_START,
    SESSION_END,
)
from logbook import Logger

log = Logger('ExchangeClock', level=LOG_LEVEL)


class SimpleClock(object):
    """Realtime clock for live trading.

    This class is a drop-in replacement for
    :class:`zipline.gens.sim_engine.MinuteSimulationClock`.

    This is a stripped down version because crypto exchanges run
    around the clock.

    The :param:`time_skew` parameter represents the time difference between
    the Broker and the live trading machine's clock.
    """

    def __init__(self, sessions, time_skew=pd.Timedelta("0s"), start=None,
                 end=None):

        self.sessions = sessions
        self.time_skew = time_skew
        self._last_emit = None
        self._before_trading_start_bar_yielded = True
        self.start = start
        self.end = end

    def __iter__(self):
        self.handle_late_start()
        yield pd.Timestamp.utcnow(), SESSION_START

        while True:
            current_time = pd.Timestamp.utcnow()
            current_minute = current_time.floor('1 min')

            if self.end is not None and current_minute >= self.end:
                break
            if self._last_emit is None or current_minute > self._last_emit:
                log.debug('emitting minutely bar: {}'.format(current_minute))

                self._last_emit = current_minute
                yield current_minute, BAR
            else:
                sleep(1)

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
