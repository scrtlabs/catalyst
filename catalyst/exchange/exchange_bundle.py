import os
from datetime import timedelta

import numpy as np
import pandas as pd
from logbook import Logger
from pandas import DatetimeIndex

from catalyst import get_calendar
from catalyst.data.minute_bars import BcolzMinuteOverlappingData, \
    BcolzMinuteBarWriter, BcolzMinuteBarReader, BcolzMinuteBarMetadata
from catalyst.data.us_equity_pricing import BcolzDailyBarWriter, \
    BcolzDailyBarReader
from catalyst.exchange.bundle_utils import get_ffill_candles, get_start_dt
from catalyst.exchange.exchange_utils import get_exchange_folder
from catalyst.utils.cli import maybe_show_progress
from catalyst.utils.paths import ensure_directory


def _cachpath(symbol, type_):
    return '-'.join([symbol, type_])


BUNDLE_NAME_TEMPLATE = '{root}/{frequency}_bundle'
log = Logger('exchange_bundle')


class ExchangeBundle:
    def __init__(self, exchange):
        self.exchange = exchange
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
        if data_frequency in self._readers \
                and self._readers[data_frequency] is not None:
            return self._readers[data_frequency]

        root = get_exchange_folder(self.exchange.name)
        input_dir = BUNDLE_NAME_TEMPLATE.format(
            root=root,
            frequency=data_frequency
        )

        self._readers[data_frequency] = None
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

    def update_metadata(self, writer, start_dt, end_dt):
        pass

    def get_writer(self, start_dt, end_dt, data_frequency):
        """
        Get a data writer object, either a new object or from cache

        :return: BcolzMinuteBarWriter or BcolzDailyBarWriter
        """
        key = data_frequency
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

                metadata = BcolzMinuteBarMetadata.read(output_dir)

                write_metadata = False
                if start_dt < metadata.start_session:
                    write_metadata = True
                    start_session = start_dt.floor('1d')
                else:
                    start_session = metadata.start_session

                if end_dt > metadata.end_session:
                    write_metadata = True

                    # TODO: workaround, improve the calendar logic?
                    if end_dt == start_dt:
                        end_dt += timedelta(days=1)

                    end_session = end_dt.floor('1d')
                else:
                    end_session = metadata.end_session

                self._writers[key] = \
                    BcolzMinuteBarWriter(
                        output_dir,
                        metadata.calendar,
                        start_session,
                        end_session,
                        metadata.minutes_per_day,
                        metadata.default_ohlc_ratio,
                        metadata.ohlc_ratios_per_sid,
                        write_metadata=write_metadata
                    )
            else:
                self._writers[key] = BcolzMinuteBarWriter(
                    rootdir=output_dir,
                    calendar=open_calendar,
                    minutes_per_day=self.minutes_per_day,
                    start_session=start_dt,
                    end_session=end_dt,
                    write_metadata=True,
                    default_ohlc_ratio=self.default_ohlc_ratio
                )

        elif data_frequency == 'daily':
            if len(os.listdir(output_dir)) > 0:
                self._writers[key] = \
                    BcolzDailyBarWriter.open(output_dir, end_dt)
            else:
                end_session = end_dt.floor('1d')
                self._writers[key] = BcolzDailyBarWriter(
                    filename=output_dir,
                    calendar=open_calendar,
                    start_session=start_dt,
                    end_session=end_session
                )
        else:
            raise ValueError(
                'invalid frequency {}'.format(data_frequency)
            )

        return self._writers[key]

    def filter_existing_assets(self, assets, start_dt, end_dt, data_frequency):
        """
        For each asset, get the close on the start and end dates of the chunk.
            If the data exists, the chunk ingestion is complete.
            If any data is missing we ingest the data.

        :param assets: list[TradingPair]
            The assets is scope.
        :param start_dt:
            The chunk start date.
        :param end_dt:
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
                    start_close = \
                        reader.get_value(asset.sid, start_dt, 'close')

                    if np.isnan(start_close):
                        has_data = False

                    else:
                        end_close = reader.get_value(asset.sid, end_dt,
                                                     'close')

                        if np.isnan(end_close):
                            has_data = False

                except Exception as e:
                    has_data = False

            else:
                has_data = False

            if not has_data:
                missing_assets.append(asset)

        return missing_assets

    def ingest_chunk(self, bar_count, end_dt, data_frequency, assets,
                     writer, previous_candle=dict()):
        """
        Retrieve the specified OHLCV chunk and write it to the bundle

        :param chunk:
        :param previous_candle:
        :param data_frequency:
        :param assets:
        :param writer:
        :return:
        """

        chunk_assets = []
        for asset in assets:
            if asset.start_date <= end_dt:
                chunk_assets.append(asset)

        start_dt = get_start_dt(end_dt, bar_count, data_frequency)
        missing_assets = self.filter_existing_assets(
            assets=chunk_assets,
            start_dt=start_dt,
            end_dt=end_dt,
            data_frequency=data_frequency
        )

        if len(missing_assets) == 0:
            log.debug('the data chunk already exists')
            return

        candles = self.exchange.get_history(
            assets=missing_assets,
            end_dt=end_dt,
            bar_count=bar_count,
            data_frequency=data_frequency
        )

        num_candles = 0
        data = []
        for asset in candles:
            asset_candles = candles[asset]
            if not asset_candles:
                log.debug(
                    'no data: {symbols} on {exchange}, date {end}'.format(
                        symbols=missing_assets,
                        exchange=self.exchange.name,
                        end=end_dt
                    )
                )
                continue

            previous = previous_candle[asset] \
                if asset in previous_candle else None

            all_dates, all_candles = get_ffill_candles(
                candles=asset_candles,
                bar_count=bar_count,
                end_dt=end_dt,
                data_frequency=data_frequency,
                previous_candle=previous
            )
            previous_candle[asset] = all_candles[-1]

            df = pd.DataFrame(
                data=all_candles,
                index=all_dates,
                columns=['open', 'high', 'low', 'close', 'volume']
            )
            if not df.empty:
                df.sort_index(inplace=True)

                sid = asset.sid
                num_candles += len(df.values)

                data.append((sid, df))

        try:
            log.debug(
                'writing {num_candles} candles for {bar_count} bars'
                'ending {end}'.format(
                    num_candles=num_candles,
                    bar_count=bar_count,
                    end=end_dt
                )
            )

            writer.write(
                data=data,
                show_progress=False,
                invalid_data_behavior='raise'
            )
        except BcolzMinuteOverlappingData as e:
            log.warn('chunk already exists: {}'.format(e))
        except Exception as e:
            log.warn('error when writing data: {}, trying again'.format(e))

            # This is workaround, there is an issue with empty
            # session_label when using a newly created writer
            del self._writers[data_frequency]

            # TODO: these are the dates of the chunk, not the job
            writer = self.get_writer(start_dt, end_dt, data_frequency)
            writer.write(
                data=data,
                show_progress=False,
                invalid_data_behavior='raise'
            )

        return data

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

        writer = self.get_writer(start, end, data_frequency)

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
                    bar_count=chunk['bar_count'],
                    end_dt=chunk['end'],
                    data_frequency=data_frequency,
                    assets=assets,
                    writer=writer,
                    previous_candle=previous_candle,
                )
