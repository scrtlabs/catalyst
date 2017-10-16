from logging import Logger

import pandas as pd

from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.init_utils import get_exchange

log = Logger('test_exchange_bundle')


class ExchangeBundleTestCase:
    def test_ingest_minute(self):
        exchange_name = 'poloniex'

        # start = pd.to_datetime('2017-09-01', utc=True)
        start = pd.to_datetime('2017-1-1', utc=True)
        end = pd.to_datetime('2017-9-30', utc=True)

        exchange_bundle = ExchangeBundle(get_exchange(exchange_name))

        log.info('ingesting exchange bundle {}'.format(exchange_name))
        exchange_bundle.ingest(
            data_frequency='minute',
            include_symbols='gno_btc',
            # include_symbols=None,
            exclude_symbols=None,
            start=start,
            end=end,
            show_progress=True
        )
        pass

    def test_ingest_minute_all(self):
        exchange_name = 'bitfinex'

        # start = pd.to_datetime('2017-09-01', utc=True)
        start = pd.to_datetime('2017-10-01', utc=True)
        end = pd.to_datetime('2017-10-05', utc=True)

        exchange_bundle = ExchangeBundle(get_exchange(exchange_name))

        log.info('ingesting exchange bundle {}'.format(exchange_name))
        exchange_bundle.ingest(
            data_frequency='minute',
            exclude_symbols=None,
            start=start,
            end=end,
            show_progress=True
        )
        pass

    def test_ingest_daily(self):
        exchange_name = 'bitfinex'

        start = pd.to_datetime('2017-09-01', utc=True)
        end = pd.Timestamp.utcnow()

        exchange_bundle = ExchangeBundle(get_exchange(exchange_name))

        log.info('ingesting exchange bundle {}'.format(exchange_name))
        exchange_bundle.ingest(
            data_frequency='daily',
            include_symbols='neo_btc',
            exclude_symbols=None,
            start=start,
            end=end,
            show_progress=True
        )
        pass

    def test_merge_ctables(self):
        exchange_name = 'poloniex'
        data_frequency = 'minute'

        exchange = get_exchange(exchange_name)
        asset = exchange.get_asset('gno_btc')

        start = pd.to_datetime('2017-5-1', utc=True)
        end = pd.to_datetime('2017-5-31', utc=True)

        exchange_bundle = ExchangeBundle(exchange)

        writer = exchange_bundle.get_writer(start, end, data_frequency)
        exchange_bundle.ingest_ctable(
            asset=asset,
            data_frequency=data_frequency,
            period='2017-5',
            writer=writer,
            verify=True
        )
        pass
