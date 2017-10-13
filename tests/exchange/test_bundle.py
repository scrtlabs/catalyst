from datetime import timedelta, time
from logging import Logger

import bcolz
from toolz.itertoolz import join as joinz
import pandas as pd

from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.init_utils import get_exchange

log = Logger('test_exchange_bundle')


class ExchangeBundleTestCase:
    def test_ingest_minute(self):
        exchange_name = 'bitfinex'

        # start = pd.to_datetime('2017-09-01', utc=True)
        start = pd.to_datetime('2017-10-01', utc=True)
        end = pd.to_datetime('2017-10-06', utc=True)

        exchange_bundle = ExchangeBundle(get_exchange(exchange_name))

        log.info('ingesting exchange bundle {}'.format(exchange_name))
        exchange_bundle.ingest(
            data_frequency='minute',
            include_symbols='bcc_btc',
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
        exchange_name = 'bitfinex'

        root = '/Users/fredfortier/.catalyst/data/exchanges/bitfinex/temp_bundles'
        path = '00/02/000284.bcolz'

        august = '{}/{}'.format(
            root, 'poloniex-minute-btc_usdt-2017-8'
        )
        exchange = get_exchange(exchange_name)
        asset = exchange.get_asset('btc_usd')

        exchange_bundle = ExchangeBundle(exchange)
        exchange_bundle.ingest_ctable(
            asset=asset,
            data_frequency='minute',
            path=august
        )

        september = '{}/{}/{}'.format(
            root, 'poloniex-minute-btc_usdt-2017-9', path
        )
        zseptember = bcolz.open(september, mode='a')

        pass
