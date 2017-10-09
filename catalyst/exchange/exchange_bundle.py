import os
from datetime import timedelta

import numpy as np
import pandas as pd
from logbook import Logger

from catalyst import get_calendar
from catalyst.data.minute_bars import BcolzMinuteOverlappingData, \
    BcolzMinuteBarWriter, BcolzMinuteBarReader
from catalyst.data.us_equity_pricing import BcolzDailyBarWriter, \
    BcolzDailyBarReader
from catalyst.exchange.bundle_utils import fetch_candles_chunk, get_history, \
    get_seconds_from_date
from catalyst.exchange.exchange_utils import get_exchange_folder
from catalyst.exchange.init_utils import get_exchange
from catalyst.utils.cli import maybe_show_progress
from catalyst.utils.paths import ensure_directory


def _cachpath(symbol, type_):
    return '-'.join([symbol, type_])


BUNDLE_NAME_TEMPLATE = '{root}/{frequency}_bundle'
log = Logger('exchange_bundle')


class ExchangeBundle:
    def __init__(self, exchange_name, ):
        self.exchange = get_exchange(exchange_name)
        self.minutes_per_day = 1440
        self.default_ohlc_ratio = 1000000
        self._writers = dict()
        self._readers = dict()

    def get_assets(self, include_symbols, exclude_symbols):
        # TODO: filter exclude symbols assets
        if include_symbols is not None:
            include_symbols_list = include_symbols.split(',')

            return self.exchange.get_assets(include_symbols_list)

        else:
            return self.exchange.get_assets()

    def get_adj_dates(self, start, end, assets):
        now = pd.Timestamp.utcnow()
        if end > now:
            log.info('adjusting the end date to now {}'.format(now))
            end = now

        earliest_trade = None
        for asset in assets:
            if earliest_trade is None or earliest_trade > asset.start_date:
                earliest_trade = asset.start_date

        if earliest_trade > start:
            log.info(
                'adjusting start date to earliest trade date found {}'.format(
                    earliest_trade
                ))
            start = earliest_trade

        if start >= end:
            raise ValueError('start date cannot be after end date')

        return start, end

    def get_reader(self, data_frequency):
        """
        Get a data writer object, either a new object or from cache

        :return: BcolzMinuteBarReader or BcolzDailyBarReader
        """
        if data_frequency in self._readers:
            return self._readers[data_frequency]

        root = get_exchange_folder(self.exchange.name)
        input_dir = BUNDLE_NAME_TEMPLATE.format(
            root=root,
            frequency=data_frequency
        )

        if data_frequency == 'minute':
            try:
                self._readers[data_frequency] = BcolzMinuteBarReader(input_dir)
            except IOError:
                log.debug('no reader data found in {}'.format(input_dir))

        elif data_frequency == 'daily':
            try:
                self._readers[data_frequency] = BcolzDailyBarReader(input_dir)
            except IOError:
                log.debug('no reader data found in {}'.format(input_dir))
        else:
            raise ValueError(
                'invalid frequency {}'.format(data_frequency)
            )

        return self._readers[data_frequency]

    def get_writer(self, data_frequency, start, end):
        """
        Get a data writer object, either a new object or from cache

        :return: BcolzMinuteBarWriter or BcolzDailyBarWriter
        """
        key = (data_frequency, start, end)
        if key in self._writers:
            return self._writers[key]

        open_calendar = get_calendar('OPEN')

        root = get_exchange_folder(self.exchange.name)
        output_dir = BUNDLE_NAME_TEMPLATE.format(
            root=root,
            frequency=data_frequency
        )
        ensure_directory(output_dir)

        if data_frequency == 'minute':
            if len(os.listdir(output_dir)) > 0:
                self._writers[key] = \
                    BcolzMinuteBarWriter.open(output_dir, end)
            else:
                self._writers[key] = BcolzMinuteBarWriter(
                    rootdir=output_dir,
                    calendar=open_calendar,
                    minutes_per_day=self.minutes_per_day,
                    start_session=start,
                    end_session=end,
                    write_metadata=True,
                    default_ohlc_ratio=self.default_ohlc_ratio
                )
        elif data_frequency == 'daily':
            if len(os.listdir(output_dir)) > 0:
                self._writers[key] = BcolzDailyBarWriter.open(output_dir, end)
            else:
                end_session = end.floor('1d')
                self._writers[key] = BcolzDailyBarWriter(
                    filename=output_dir,
                    calendar=open_calendar,
                    start_session=start,
                    end_session=end_session
                )
        else:
            raise ValueError(
                'invalid frequency {}'.format(data_frequency)
            )

        return self._writers[key]

    def filter_existing_assets(self, assets, start, end, data_frequency):
        """
        For each asset, get the close on the start and end dates of the chunk.
            If the data exists, the chunk ingestion is complete.
            If any data is missing we ingest the data.

        :param assets: list[TradingPair]
            The assets is scope.
        :param start:
            The chunk start date.
        :param end:
            The chunk end date.
        :return: list[TradingPair]
            The assets missing from the bundle
        """
        reader = self.get_reader(data_frequency)
        missing_assets = []
        for asset in assets:
            has_data = True
            if has_data and reader is not None:
                try:
                    start_close = reader.get_value(asset.sid, start, 'close')

                    if np.isnan(start_close):
                        has_data = False

                    else:
                        end_close = reader.get_value(asset.sid, end, 'close')

                        if np.isnan(end_close):
                            has_data = False

                except Exception as e:
                    has_data = False

            else:
                has_data = False

            if not has_data:
                missing_assets.append(asset)

        return missing_assets

    def ingest_chunk(self, chunk, previous_candle, data_frequency, assets,
                     writer):
        chunk_end = chunk['end']
        chunk_start = chunk_end - timedelta(minutes=chunk['bar_count'])

        chunk_assets = []
        for asset in assets:
            if asset.start_date <= chunk_end:
                chunk_assets.append(asset)

        missing_assets = self.filter_existing_assets(
            assets=chunk_assets,
            start=chunk_start,
            end=chunk_end,
            data_frequency=data_frequency
        )

        if len(missing_assets) == 0:
            log.debug('the data chunk already exists')
            return

        candles = dict()
        for asset in missing_assets:
            if chunk_start < asset.end_minute:
                # TODO: fetch delta candles from exchanges
                history_end = chunk_end \
                    if chunk_end <= asset.end_minute else asset.end_minute

                # TODO: switch to Catalyst symbol convention
                candles[asset] = get_history(
                    exchange_name=self.exchange.name,
                    data_frequency=data_frequency,
                    symbol=asset.exchange_symbol,
                    start=chunk_start,
                    end=history_end
                )
            else:
                log.debug(
                    'no data in Catalyst api for chunk '
                    '{} to {}'.format(chunk_start, chunk_end)
                )
        # if data_frequency == 'minute':
        #     # TODO: ensure correct behavior for assets starting in the chunk
        #     candles = fetch_candles_chunk(
        #         exchange=self.exchange,
        #         assets=missing_assets,
        #         data_frequency=data_frequency,
        #         end_dt=chunk_end,
        #         bar_count=chunk['bar_count']
        #     )
        # else:

        num_candles = 0
        data = []
        for asset in candles:
            asset_candles = candles[asset]
            if not asset_candles:
                log.debug(
                    'no data: {symbols} on {exchange}, date {end}'.format(
                        symbols=missing_assets,
                        exchange=self.exchange.name,
                        end=chunk_end
                    )
                )
                continue

            all_dates = []
            all_candles = []
            date = chunk_start
            while date <= chunk_end:

                previous = previous_candle[asset] \
                    if asset in previous_candle else None

                candle = next((candle for candle in asset_candles \
                               if candle['last_traded'] == date),
                              previous)

                if candle is not None:
                    all_dates.append(date)
                    all_candles.append(candle)

                    previous_candle[asset] = candle

                date += timedelta(minutes=1)

            df = pd.DataFrame(all_candles, index=all_dates)
            if not df.empty:
                df.sort_index(inplace=True)

                sid = asset.sid
                num_candles += len(df.values)

                data.append((sid, df))

        try:
            log.debug(
                'writing {num_candles} candles from {start} to {end}'.format(
                    num_candles=num_candles,
                    start=chunk_start,
                    end=chunk_end
                )
            )

            for pair in data:
                log.debug('data for sid {}\n{}\n{}'.format(
                    pair[0], pair[1].head(2), pair[1].tail(2)))

            writer.write(
                data=data,
                show_progress=False,
                invalid_data_behavior='raise'
            )
        except BcolzMinuteOverlappingData as e:
            log.warn('chunk already exists {}: {}'.format(chunk, e))

    def ingest(self, data_frequency, include_symbols=None,
               exclude_symbols=None, start=None, end=None,
               show_progress=True, environ=os.environ):
        """
        Ingest the bundle

        :param data_frequency:
        :param include_symbols:
        :param exclude_symbols:
        :param start:
        :param end:
        :param show_progress:
        :param environ:
        :return:
        """

        assets = self.get_assets(include_symbols, exclude_symbols)
        start, end = self.get_adj_dates(start, end, assets)

        symbols = []
        log.debug(
            'ingesting trading pairs {symbols} on exchange {exchange} '
            'from {start} to {end}'.format(
                symbols=symbols,
                exchange=self.exchange.name,
                start=start,
                end=end
            )
        )

        delta = end - start
        if data_frequency == 'minute':
            delta_periods = delta.total_seconds() / 60

        elif data_frequency == 'daily':
            delta_periods = delta.total_seconds() / 60 / 60 / 24

        else:
            raise ValueError('frequency not supported')

        writer = self.get_writer(data_frequency, start, end)

        if delta_periods > self.exchange.num_candles_limit:
            bar_count = self.exchange.num_candles_limit

            chunks = []
            last_chunk_date = end.floor('1 min')
            while last_chunk_date > start + timedelta(minutes=bar_count):
                # TODO: account for the partial last bar
                chunk = dict(end=last_chunk_date, bar_count=bar_count)
                chunks.append(chunk)

                # TODO: base on frequency
                last_chunk_date = \
                    last_chunk_date - timedelta(minutes=(bar_count + 1))

            chunks.reverse()

        else:
            chunks = [dict(end=end, bar_count=delta_periods)]

        with maybe_show_progress(
                chunks,
                show_progress,
                label='Fetching {exchange} {frequency} candles: '.format(
                    exchange=self.exchange.name,
                    frequency=data_frequency
                )) as it:

            previous_candle = dict()
            for chunk in it:
                self.ingest_chunk(
                    chunk=chunk,
                    previous_candle=previous_candle,
                    data_frequency=data_frequency,
                    assets=assets,
                    writer=writer
                )
