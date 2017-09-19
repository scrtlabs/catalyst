from datetime import timedelta

import os
import pandas as pd
from logging import Logger

from catalyst import get_calendar

from catalyst.data.minute_bars import BcolzMinuteBarWriter
from catalyst.exchange.exchange_bundle import exchange_bundle
from catalyst.exchange.exchange_utils import get_exchange_minute_writer_root

log = Logger('test_exchange_bundle')


class ExchangeBundleTestCase:
    def test_ingest(self):
        exchange_name = 'bitfinex'

        start = pd.Timestamp.utcnow() - timedelta(days=2)
        end = pd.Timestamp.utcnow()
        open_calendar = get_calendar('OPEN')

        root = get_exchange_minute_writer_root(exchange_name)
        filename = os.path.join(root, 'metadata.json')

        if os.path.isfile(filename):
            minute_bar_writer = BcolzMinuteBarWriter.open(root, end)
        else:
            # TODO: need to be able to write more precise numbers
            minute_bar_writer = BcolzMinuteBarWriter(
                rootdir=root,
                calendar=open_calendar,
                minutes_per_day=1440,
                start_session=start.floor('1d'),
                end_session=end,
                write_metadata=True
            )

        ingest = exchange_bundle(
            exchange_name=exchange_name,
            symbols=['btc_usd']
        )

        ingest(
            environ=os.environ,
            asset_db_writer=None,  # TODO: nice to have
            minute_bar_writer=minute_bar_writer,
            daily_bar_writer=None,  # TODO: add later
            adjustment_writer=None,  # Not applicable to crypto
            calendar=open_calendar,
            start_session=start,
            end_session=end,
            cache=dict(),
            show_progress=True,
            output_dir=exchange_name,  # TODO: not sure
            start=start,
            end=end
        )
        pass
