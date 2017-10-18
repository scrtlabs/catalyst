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
        exchange_name = 'poloniex'

        # Switch between daily and minute for testing
        data_frequency = 'daily'
        # data_frequency = 'minute'

        exchange = get_exchange(exchange_name)
        assets = [
            exchange.get_asset('eth_btc'),
            exchange.get_asset('etc_btc'),
        ]

        start = pd.to_datetime('2017-9-1', utc=True)
        end = pd.to_datetime('2017-9-30', utc=True)

        exchange_bundle = ExchangeBundle(exchange)

        writer = exchange_bundle.get_writer(start, end, data_frequency)

        # In the interest of avoiding abstractions, this is writing a chunk
        # to the ctable. It does not include the logic which creates chunks.
        exchange_bundle.ingest_ctable(
            asset=assets[0],
            data_frequency=data_frequency,
            # period='2017-9',
            period='2017',
            # Dont't forget to update if you change your dates
            start_dt=start,
            end_dt=end,
            writer=writer,
            empty_rows_behavior='strip'
        )
        exchange_bundle.ingest_ctable(
            asset=assets[1],
            data_frequency=data_frequency,
            # period='2017-9',
            period='2017',
            start_dt=start,
            end_dt=end,
            writer=writer,
            empty_rows_behavior='strip'
        )

        # Since this pair was loaded last. It should be there in daily mode.
        last_asset_array = exchange_bundle.get_raw_arrays(
            assets=[assets[1]],
            start_dt=start,
            end_dt=end,
            fields=['close'],
            data_frequency=data_frequency
        )
        print('found {} rows for last ingestion'.format(
            len(last_asset_array[0]))
        )

        # In daily mode, this returns an error. It appears that writing
        # a second asset in the same date range removed the first asset.

        # In minute mode, the data is there too. This signals that the minute
        # writer / reader is more powerful. This explains why I did not
        # encounter these problems as I have been focusing on minute data.
        first_asset_array = exchange_bundle.get_raw_arrays(
            assets=[assets[0]],
            start_dt=start,
            end_dt=end,
            fields=['close'],
            data_frequency=data_frequency
        )
        print('found {} rows for first ingestion'.format(
            len(first_asset_array[0]))
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

        pass
