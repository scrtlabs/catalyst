import os
from datetime import timedelta
from logging import Logger, DEBUG

import pandas as pd

from catalyst import get_calendar
from catalyst.data.minute_bars import BcolzMinuteBarWriter
from catalyst.exchange.exchange_bundle import exchange_bundle
from catalyst.utils.paths import ensure_directory, data_root

log = Logger('test_exchange_bundle')


class ExchangeBundleTestCase:
    def test_ingest(self):
        exchange_name = 'bitfinex'

        start = pd.Timestamp.utcnow() - timedelta(days=365)
        end = pd.Timestamp.utcnow()
        open_calendar = get_calendar('OPEN')

        root = data_root(os.environ)
        output_dir = '{root}/exchange_{exchange}/test'.format(
            root=root,
            exchange=exchange_name
        )
        ensure_directory(output_dir)

        filename = os.path.join(output_dir, 'metadata.json')

        start_session = start.floor('1d')
        if os.path.isfile(filename):
            minute_bar_writer = BcolzMinuteBarWriter.open(output_dir, end)
        else:
            # TODO: need to be able to write more precise numbers
            minute_bar_writer = BcolzMinuteBarWriter(
                rootdir=output_dir,
                calendar=open_calendar,
                minutes_per_day=1440,
                start_session=start_session,
                end_session=end,
                write_metadata=True
            )

        ingest = exchange_bundle(
            exchange_name=exchange_name,
            symbols=['eth_btc'],
            log_level=DEBUG
        )

        ingest(environ=os.environ,
               asset_db_writer=None,
               minute_bar_writer=minute_bar_writer,
               five_minute_bar_writer=None,
               daily_bar_writer=None,
               adjustment_writer=None,
               calendar=open_calendar,
               start_session=start_session,
               end_session=end,
               cache=dict(),
               show_progress=True,
               is_compile=False,
               output_dir=output_dir,
               start=start,
               end=end)
        pass
