from unittest import TestCase
from logbook import Logger
from mock import patch, sentinel
from catalyst.exchange.simple_clock import SimpleClock
from catalyst.utils.calendars.trading_calendar import days_at_time
from datetime import time
from collections import defaultdict
from catalyst.utils.calendars import get_calendar
import pandas as pd

log = Logger('ExchangeClockTestCase')


class TestExchangeClockTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.open_calendar = get_calendar("OPEN")

        cls.sessions = pd.Timestamp.utcnow()

    def setUp(self):
        self.internal_clock = None
        self.events = defaultdict(list)

    def advance_clock(self, x):
        """Mock function for sleep. Advances the internal clock by 1 min"""
        # The internal clock advance time must be 1 minute to match
        # MinutesSimulationClock's update frequency
        self.internal_clock += pd.Timedelta('1 min')

    def get_clock(self, arg, *args, **kwargs):
        """Mock function for pandas.to_datetime which is used to query the
        current time in RealtimeClock"""
        assert arg == "now"
        return self.internal_clock

    def test_clock(self):
        with patch('catalyst.exchange.simple_clock.pd.to_datetime') as to_dt, \
                patch('catalyst.exchange.simple_clock.sleep') as sleep:
            clock = SimpleClock(sessions=self.sessions)
            to_dt.side_effect = self.get_clock
            sleep.side_effect = self.advance_clock
            start_time = pd.Timestamp.utcnow()
            self.internal_clock = start_time

            events = list(clock)

            # Event 0 is SESSION_START which always happens at 00:00.
            ts, event_type = events[1]
        pass
