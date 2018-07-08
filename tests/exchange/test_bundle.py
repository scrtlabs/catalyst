# import hashlib
import os
import tempfile
from logging import getLogger

import pandas as pd

from catalyst.exchange.exchange_bcolz import BcolzExchangeBarReader, \
    BcolzExchangeBarWriter
from catalyst.exchange.exchange_bundle import ExchangeBundle, \
    BUNDLE_NAME_TEMPLATE
from catalyst.exchange.utils.bundle_utils import get_bcolz_chunk, \
    get_df_from_arrays
from catalyst.exchange.utils.datetime_utils import get_start_dt
from catalyst.exchange.utils.exchange_utils import get_exchange_folder
from catalyst.exchange.utils.factory import get_exchange
from catalyst.exchange.utils.stats_utils import df_to_string
from catalyst.utils.paths import ensure_directory

log = getLogger('test_exchange_bundle')


class TestExchangeBundle:
    def test_spot_value(self):
        # data_frequency = 'daily'
        # exchange_name = 'poloniex'

        # exchange = get_exchange(exchange_name)
        # exchange_bundle = ExchangeBundle(exchange)
        # assets = [
        #     exchange.get_asset('btc_usdt')
        # ]
        # dt = pd.to_datetime('2017-10-14', utc=True)

        # values = exchange_bundle.get_spot_values(
        #     assets=assets,
        #     field='close',
        #     dt=dt,
        #     data_frequency=data_frequency
        # )
        pass

    def _test_ingest_minute(self):
        data_frequency = 'minute'
        exchange_name = 'binance'

        exchange = get_exchange(exchange_name)
        exchange_bundle = ExchangeBundle(exchange)
        assets = [
            exchange.get_asset('eth_btc')
        ]

        start = pd.to_datetime('2018-03-01', utc=True)
        end = pd.to_datetime('2018-03-8', utc=True)

        log.info('ingesting exchange bundle {}'.format(exchange_name))
        exchange_bundle.ingest(
            data_frequency=data_frequency,
            include_symbols=','.join([asset.symbol for asset in assets]),
            # include_symbols=None,
            exclude_symbols=None,
            start=start,
            end=end,
            show_progress=True
        )

        reader = exchange_bundle.get_reader(data_frequency)
        for asset in assets:
            arrays = reader.load_raw_arrays(
                sids=[asset.sid],
                fields=['close'],
                start_dt=start,
                end_dt=end
            )
            print('found {} rows for {} ingestion\n{}'.format(
                len(arrays[0]), asset.symbol, arrays[0])
            )
        pass

    def _test_ingest_minute_all(self):
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

    def _test_ingest_exchange(self):
        # exchange_name = 'bitfinex'
        # data_frequency = 'daily'
        # include_symbols = 'neo_btc,bch_btc,eth_btc'

        exchange_name = 'binance'
        data_frequency = 'minute'

        exchange = get_exchange(exchange_name)
        exchange_bundle = ExchangeBundle(exchange)

        log.info('ingesting exchange bundle {}'.format(exchange_name))
        exchange_bundle.ingest(
            data_frequency=data_frequency,
            include_symbols=None,
            exclude_symbols=None,
            start=None,
            end=None,
            show_progress=True
        )

        pass

    def _test_ingest_daily(self):
        exchange_name = 'bitfinex'
        data_frequency = 'minute'
        include_symbols = 'neo_btc'

        # exchange_name = 'poloniex'
        # data_frequency = 'daily'
        # include_symbols = 'eth_btc'

        # start = pd.to_datetime('2017-1-1', utc=True)
        # end = pd.to_datetime('2017-10-16', utc=True)
        # periods = get_periods_range(start, end, data_frequency)

        start = None
        end = None
        exchange = get_exchange(exchange_name)
        exchange_bundle = ExchangeBundle(exchange)

        log.info('ingesting exchange bundle {}'.format(exchange_name))
        exchange_bundle.ingest(
            data_frequency=data_frequency,
            include_symbols=include_symbols,
            exclude_symbols=None,
            start=start,
            end=end,
            show_progress=True
        )

        symbols = include_symbols.split(',')
        assets = []
        for pair_symbol in symbols:
            assets.append(exchange.get_asset(pair_symbol))

        reader = exchange_bundle.get_reader(data_frequency)
        start_dt = reader.first_trading_day
        end_dt = reader.last_available_dt

        if data_frequency == 'daily':
            end_dt = end_dt - pd.Timedelta(hours=23, minutes=59)

        for asset in assets:
            arrays = reader.load_raw_arrays(
                sids=[asset.sid],
                fields=['close'],
                start_dt=start_dt,
                end_dt=end_dt
            )
            print('found {} rows for {} ingestion\n{}'.format(
                len(arrays[0]), asset.symbol, arrays[0])
            )
        pass

    def _test_merge_ctables(self):
        exchange_name = 'bittrex'

        # Switch between daily and minute for testing
        # data_frequency = 'daily'
        data_frequency = 'daily'

        exchange = get_exchange(exchange_name)
        assets = [
            exchange.get_asset('eth_btc'),
            exchange.get_asset('etc_btc'),
            exchange.get_asset('wings_eth'),
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
                period='2017',
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
        reader = exchange_bundle.get_reader(data_frequency)
        for asset in assets:
            # Since this pair was loaded last. It should be here in daily mode.
            arrays = reader.load_raw_arrays(
                sids=[asset.sid],
                fields=['close'],
                start_dt=start,
                end_dt=end
            )
            print('found {} rows for {} ingestion\n{}'.format(
                len(arrays[0]), asset.symbol, arrays[0])
            )
        pass

    def _test_daily_data_to_minute_table(self):
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

    def _test_minute_bundle(self):
        # exchange_name = 'poloniex'
        # data_frequency = 'minute'

        # exchange = get_exchange(exchange_name)
        # asset = exchange.get_asset('neos_btc')

        # path = get_bcolz_chunk(
        #     exchange_name=exchange_name,
        #     symbol=asset.symbol,
        #     data_frequency=data_frequency,
        #     period='2017-5',
        # )
        pass

    def _test_hash_symbol(self):
        # symbol = 'etc_btc'
        # sid = int(
        #     hashlib.sha256(symbol.encode('utf-8')).hexdigest(), 16
        # ) % 10 ** 6
        pass

    def _test_validate_data(self):
        exchange_name = 'bitfinex'
        data_frequency = 'minute'

        exchange = get_exchange(exchange_name)
        exchange_bundle = ExchangeBundle(exchange)
        assets = [exchange.get_asset('iot_btc')]

        end_dt = pd.to_datetime('2017-9-2 1:00', utc=True)
        bar_count = 60

        bundle_series = exchange_bundle.get_history_window_series(
            assets=assets,
            end_dt=end_dt,
            bar_count=bar_count * 5,
            field='close',
            data_frequency='minute',
        )
        candles = exchange.get_candles(
            assets=assets,
            end_dt=end_dt,
            bar_count=bar_count,
            freq='1T'
        )
        start_dt = get_start_dt(end_dt, bar_count, data_frequency)

        frames = []
        for asset in assets:
            bundle_df = pd.DataFrame(
                data=dict(bundle_price=bundle_series[asset]),
                index=bundle_series[asset].index
            )
            exchange_series = exchange.get_series_from_candles(
                candles=candles[asset],
                start_dt=start_dt,
                end_dt=end_dt,
                data_frequency=data_frequency,
                field='close'
            )
            exchange_df = pd.DataFrame(
                data=dict(exchange_price=exchange_series),
                index=exchange_series.index
            )

            df = exchange_df.join(bundle_df, how='left')
            df['last_traded'] = df.index
            df['asset'] = asset.symbol
            df.set_index(['asset', 'last_traded'], inplace=True)

            frames.append(df)

        df = pd.concat(frames)
        print('\n' + df_to_string(df))
        pass

    def _test_ingest_candles(self):
        exchange_name = 'bitfinex'
        data_frequency = 'minute'

        exchange = get_exchange(exchange_name)
        bundle = ExchangeBundle(exchange)
        assets = [exchange.get_asset('iot_btc')]

        end_dt = pd.to_datetime('2017-10-20', utc=True)
        bar_count = 100

        start_dt = get_start_dt(end_dt, bar_count, data_frequency)
        candles = exchange.get_candles(
            assets=assets,
            start_dt=start_dt,
            end_dt=end_dt,
            bar_count=bar_count,
            freq='1T'
        )

        writer = bundle.get_writer(start_dt, end_dt, data_frequency)
        for asset in assets:
            dates = [candle['last_traded'] for candle in candles[asset]]

            values = dict()
            for field in ['open', 'high', 'low', 'close', 'volume']:
                values[field] = [candle[field] for candle in candles[asset]]

            periods = bundle.get_calendar_periods_range(
                start_dt, end_dt, data_frequency
            )
            df = pd.DataFrame(values, index=dates)
            df = df.loc[periods].fillna(method='ffill')

            # TODO: why do I get an extra bar?
            bundle.ingest_df(
                ohlcv_df=df,
                data_frequency=data_frequency,
                asset=asset,
                writer=writer,
                empty_rows_behavior='raise',
                duplicates_behavior='raise'
            )

        bundle_series = bundle.get_history_window_series(
            assets=assets,
            end_dt=end_dt,
            bar_count=bar_count,
            field='close',
            data_frequency=data_frequency,
            reset_reader=True
        )
        df = pd.DataFrame(bundle_series)
        print('\n' + df_to_string(df))
        pass

    def main_bundle_to_csv(self):
        exchange_name = 'poloniex'
        data_frequency = 'minute'

        exchange = get_exchange(exchange_name)
        asset = exchange.get_asset('eth_btc')

        start_dt = pd.to_datetime('2016-5-31', utc=True)
        end_dt = pd.to_datetime('2016-6-1', utc=True)
        self._bundle_to_csv(
            asset=asset,
            exchange_name=exchange.name,
            data_frequency=data_frequency,
            filename='{}_{}_{}'.format(
                exchange_name, data_frequency, asset.symbol
            ),
            start_dt=start_dt,
            end_dt=end_dt
        )

    def bundle_to_csv(self):
        exchange_name = 'poloniex'
        data_frequency = 'minute'
        period = '2017-01'
        symbol = 'eth_btc'

        exchange = get_exchange(exchange_name)
        asset = exchange.get_asset(symbol)

        path = get_bcolz_chunk(
            exchange_name=exchange.name,
            symbol=asset.symbol,
            data_frequency=data_frequency,
            period=period
        )
        self._bundle_to_csv(
            asset=asset,
            exchange_name=exchange.name,
            data_frequency=data_frequency,
            path=path,
            filename=period
        )
        pass

    def _bundle_to_csv(self, asset, exchange_name, data_frequency, filename,
                       path=None, start_dt=None, end_dt=None):
        bundle = ExchangeBundle(exchange_name)
        reader = bundle.get_reader(data_frequency, path=path)

        if start_dt is None:
            start_dt = reader.first_trading_day

        if end_dt is None:
            end_dt = reader.last_available_dt

        if data_frequency == 'daily':
            end_dt = end_dt - pd.Timedelta(hours=23, minutes=59)

        arrays = None
        try:
            arrays = reader.load_raw_arrays(
                sids=[asset.sid],
                fields=['open', 'high', 'low', 'close', 'volume'],
                start_dt=start_dt,
                end_dt=end_dt
            )
        except Exception as e:
            log.warn('skipping ctable for {} from {} to {}: {}'.format(
                asset.symbol, start_dt, end_dt, e
            ))

        periods = bundle.get_calendar_periods_range(
            start_dt, end_dt, data_frequency
        )
        df = get_df_from_arrays(arrays, periods)

        folder = os.path.join(
            tempfile.gettempdir(), 'catalyst', exchange_name, asset.symbol
        )
        ensure_directory(folder)

        path = os.path.join(folder, filename + '.csv')

        log.info('creating csv file: {}'.format(path))
        print('HEAD\n{}'.format(df.head(100)))
        print('TAIL\n{}'.format(df.tail(100)))
        df.to_csv(path)
        pass

    def _test_ingest_csv(self):
        data_frequency = 'minute'
        exchange_name = 'bittrex'
        path = '/Users/fredfortier/Dropbox/Enigma/Data/bittrex_bat_eth.csv'

        exchange_bundle = ExchangeBundle(exchange_name)
        exchange_bundle.ingest_csv(path, data_frequency)

        exchange = get_exchange(exchange_name)
        asset = exchange.get_asset('bat_eth')

        start_dt = pd.to_datetime('2017-6-3', utc=True)
        end_dt = pd.to_datetime('2017-8-3 19:24', utc=True)
        self._bundle_to_csv(
            asset=asset,
            exchange_name=exchange.name,
            data_frequency=data_frequency,
            filename='{}_{}_{}'.format(
                exchange_name, data_frequency, asset.symbol
            ),
            start_dt=start_dt,
            end_dt=end_dt
        )
        pass
