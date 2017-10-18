from logging import Logger

import pandas as pd

from catalyst import get_calendar
from catalyst.exchange.bundle_utils import get_bcolz_chunk
from catalyst.exchange.exchange_bcolz import BcolzExchangeBarReader, \
    BcolzExchangeBarWriter
from catalyst.exchange.exchange_bundle import ExchangeBundle, \
    BUNDLE_NAME_TEMPLATE
from catalyst.exchange.exchange_utils import get_exchange_folder
from catalyst.exchange.init_utils import get_exchange
from catalyst.utils.paths import ensure_directory

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
        # data_frequency = 'daily'
        data_frequency = 'minute'

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
        for asset in assets:
            exchange_bundle.ingest_ctable(
                asset=asset,
                data_frequency=data_frequency,
                # period='2017-9',
                period='2017-9',
                # Dont't forget to update if you change your dates
                start_dt=start,
                end_dt=end,
                writer=writer,
                empty_rows_behavior='strip'
            )

        # In daily mode, this returns an error. It appears that writing
        # a second asset in the same date range removed the first asset.

        # In minute mode, the data is there too. This signals that the minute
        # writer / reader is more powerful. This explains why I did not
        # encounter these problems as I have been focusing on minute data.
        reader = self.get_reader(data_frequency)
        for asset in assets:
            # Since this pair was loaded last. It should be there in daily mode.
            arrays = reader.load_raw_arrays(
                sids=[asset.sid],
                fields=['close'],
                start_dt=start,
                end_dt=end
            )
            print('found {} rows for {} ingestion'.format(
                len(arrays[0]), asset.symbol)
            )
        pass

    def test_daily_data_to_minute_table(self):
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

        # Preparing the bundle folder
        root = get_exchange_folder(exchange.name)
        path = BUNDLE_NAME_TEMPLATE.format(
            root=root,
            frequency=data_frequency
        )
        ensure_directory(path)

        exchange_bundle = ExchangeBundle(exchange)
        calendar = get_calendar('OPEN')

        # We are using a BcolzMinuteBarWriter even though the data is daily
        # Each day has a maximum of one bar

        # I tried setting the minutes_per_day to 1 will not create
        # unnecessary bars
        writer = BcolzExchangeBarWriter(
            rootdir=path,
            data_frequency=data_frequency,
            start_session=start,
            end_session=end,
            write_metadata=True
        )

        # This will read the daily data in a bundle created by
        # the daily writer. It will write to the minute writer which
        # we are passing.

        # Ingesting a second asset to ensure that multiple chunks
        # don't override each other
        for asset in assets:
            exchange_bundle.ingest_ctable(
                asset=asset,
                data_frequency=data_frequency,
                period='2017',
                start_dt=start,
                end_dt=end,
                writer=writer,
                empty_rows_behavior='strip'
            )

        reader = BcolzExchangeBarReader(rootdir=path,
                                        data_frequency=data_frequency)

        # Reading the two assets to ensure that no data was lost
        for asset in assets:
            sid = asset.sid

            daily_values = reader.load_raw_arrays(
                fields=['open', 'high', 'low', 'close', 'volume'],
                start_dt=start,
                end_dt=end,
                sids=[sid],
            )

            print('found {} rows for last ingestion'.format(
                len(daily_values[0]))
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
