from logging import Logger

import pandas as pd

from catalyst.data.minute_bars import BcolzMinuteBarReader
from catalyst.exchange.bundle_utils import get_bcolz_chunk
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.init_utils import get_exchange

log = Logger('test_exchange_bundle')


class ExchangeBundleTestCase:
    def test_ingest_minute(self):
        exchange_name = 'poloniex'

        # start = pd.to_datetime('2017-09-01', utc=True)
        start = pd.to_datetime('2017-9-1', utc=True)
        end = pd.to_datetime('2017-9-30', utc=True)

        exchange_bundle = ExchangeBundle(get_exchange(exchange_name))

        log.info('ingesting exchange bundle {}'.format(exchange_name))
        exchange_bundle.ingest(
            data_frequency='daily',
            include_symbols='etc_btc',
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

        start = pd.to_datetime('2017-01-01', utc=True)
        end = pd.to_datetime('2017-09-30', utc=True)

        exchange_bundle = ExchangeBundle(get_exchange(exchange_name))

        log.info('ingesting exchange bundle {}'.format(exchange_name))
        exchange_bundle.ingest(
            data_frequency='daily',
            include_symbols='neo_btc,bch_btc,eth_btc',
            exclude_symbols=None,
            start=start,
            end=end,
            show_progress=True
        )
        pass

    def test_merge_ctables(self):
        exchange_name = 'bitfinex'
        data_frequency = 'daily'

        exchange = get_exchange(exchange_name)
        asset = exchange.get_asset('neo_btc')

        start = pd.to_datetime('2017-9-1', utc=True)
        end = pd.to_datetime('2017-9-30', utc=True)

        # asset = exchange.get_asset('neo_btc')
        #
        # start = pd.to_datetime('2017-9-1', utc=True)
        # end = pd.to_datetime('2017-9-30', utc=True)

        exchange_bundle = ExchangeBundle(exchange)

        writer = exchange_bundle.get_writer(start, end, data_frequency)
        exchange_bundle.ingest_ctable(
            asset=asset,
            data_frequency=data_frequency,
            period='2017',
            writer=writer,
            empty_rows_behavior='strip'
        )
        pass

    def test_minute_bundle(self):
        exchange_name = 'poloniex'
        data_frequency = 'minute'

        exchange = get_exchange(exchange_name)
        asset = exchange.get_asset('neo_btc')

        path = get_bcolz_chunk(
            exchange_name=exchange_name,
            symbol=asset.symbol,
            data_frequency=data_frequency,
            period='2017-5',
        )
        reader = BcolzMinuteBarReader(path)
        pass
