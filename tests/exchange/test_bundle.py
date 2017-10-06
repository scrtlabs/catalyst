from logging import Logger

import pandas as pd

from catalyst.exchange.exchange_bundle import ExchangeBundle

log = Logger('test_exchange_bundle')


class ExchangeBundleTestCase:
    def test_ingest(self):
        exchange_name = 'bitfinex'

        start = pd.to_datetime('2017-09-01', utc=True)
        end = pd.Timestamp.utcnow()

        log.info('ingesting exchange bundle {}'.format(exchange_name))
        exchange_bundle = ExchangeBundle(
            exchange_name=exchange_name,
            data_frequency='minute',
            include_symbols='neo_btc',
            exclude_symbols=None,
            start=start,
            end=end,
            show_progress=True
        )
        exchange_bundle.ingest()
        pass
