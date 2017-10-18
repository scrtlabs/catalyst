import os
import shutil
from datetime import timedelta

import pandas as pd
from logbook import Logger, INFO

from catalyst import get_calendar
from catalyst.data.minute_bars import BcolzMinuteOverlappingData, \
    BcolzMinuteBarMetadata
from catalyst.exchange.bundle_utils import get_ffill_candles, range_in_bundle, \
    get_bcolz_chunk, get_delta, get_adj_dates, get_month_start_end, \
    get_year_start_end, get_periods_range
from catalyst.exchange.exchange_bcolz import BcolzExchangeBarReader, \
    BcolzExchangeBarWriter
from catalyst.exchange.exchange_errors import EmptyValuesInBundleError, \
    InvalidHistoryFrequencyError, PricingDataBeforeTradingError
from catalyst.exchange.exchange_utils import get_exchange_folder
from catalyst.utils.cli import maybe_show_progress
from catalyst.utils.paths import ensure_directory


def _cachpath(symbol, type_):
    return '-'.join([symbol, type_])


BUNDLE_NAME_TEMPLATE = '{root}/{frequency}_bundle'
log = Logger('exchange_bundle')
log.level = INFO


class ExchangeBundle:
    def __init__(self, exchange):
        self.exchange = exchange
        self.minutes_per_day = 1440
        self.default_ohlc_ratio = 1000000
        self._writers = dict()
        self._readers = dict()
        self.calendar = get_calendar('OPEN')

    def get_assets(self, include_symbols, exclude_symbols):
        # TODO: filter exclude symbols assets
        if include_symbols is not None:
            include_symbols_list = include_symbols.split(',')

            return self.exchange.get_assets(include_symbols_list)

        else:
            return self.exchange.get_assets()

    def get_reader(self, data_frequency, path=None):
        """
        Get a data writer object, either a new object or from cache

        :return: BcolzMinuteBarReader or BcolzDailyBarReader
        """
        if path is None:
            root = get_exchange_folder(self.exchange.name)
            path = BUNDLE_NAME_TEMPLATE.format(
                root=root,
                frequency=data_frequency
            )

        if path in self._readers and self._readers[path] is not None:
            return self._readers[path]

        try:
            self._readers[path] = BcolzExchangeBarReader(
                rootdir=path,
                data_frequency=data_frequency
            )
        except IOError:
            self.get_readers[path] = None

        return self._readers[path]

    def update_metadata(self, writer, start_dt, end_dt):
        pass

    def get_writer(self, start_dt, end_dt, data_frequency):
        """
        Get a data writer object, either a new object or from cache

        :return: BcolzMinuteBarWriter or BcolzDailyBarWriter
        """
        root = get_exchange_folder(self.exchange.name)
        path = BUNDLE_NAME_TEMPLATE.format(
            root=root,
            frequency=data_frequency
        )

        if path in self._writers:
            return self._writers[path]

        ensure_directory(path)

        if len(os.listdir(path)) > 0:

            metadata = BcolzMinuteBarMetadata.read(path)

            write_metadata = False
            if start_dt < metadata.start_session:
                write_metadata = True
                start_session = start_dt
            else:
                start_session = metadata.start_session

            if end_dt > metadata.end_session:
                write_metadata = True

                end_session = end_dt
            else:
                end_session = metadata.end_session

            self._writers[path] = \
                BcolzExchangeBarWriter(
                    rootdir=path,
                    start_session=start_session,
                    end_session=end_session,
                    write_metadata=write_metadata,
                    data_frequency=data_frequency
                )
        else:
            self._writers[path] = BcolzExchangeBarWriter(
                rootdir=path,
                start_session=start_dt,
                end_session=end_dt,
                write_metadata=True,
                data_frequency=data_frequency
            )

        return self._writers[path]

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
            has_data = range_in_bundle(asset, start_dt, end_dt, reader)

            if not has_data:
                missing_assets.append(asset)

        return missing_assets

    def _write(self, data, writer, data_frequency):
        """
        Write data to the writer

        :param df:
        :param writer:
        :return:
        """
        try:
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
            key = writer._rootdir if data_frequency == 'minute' \
                else writer._filename

            del self._writers[key]

            writer = self.get_writer(writer._start_session,
                                     writer._end_session, data_frequency)
            writer.write(
                data=data,
                show_progress=False,
                invalid_data_behavior='raise'
            )

    def ingest_candles(self, candles, bar_count, start_dt, end_dt,
                       data_frequency,
                       previous_candle=dict()):
        """
        Ingest candles obtained via the get_candles API of an exchange.

        Since exchange APIs generally only do not return candles when there
        are no transactions in the period, we ffill values using the
        previous candle to ensure that each period has a candle.

        :param bar_count:
        :param end_dt:
        :param data_frequency:
        :param asset:
        :param writer:
        :param previous_candle
        :return:
        """

        writer = self.get_writer(start_dt, end_dt, data_frequency)

        num_candles = 0
        data = []
        for asset in candles:
            asset_candles = candles[asset]
            if not asset_candles:
                log.debug(
                    'no data: {symbols} on {exchange}, date {end}'.format(
                        symbols=asset,
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

        log.debug(
            'writing {num_candles} candles for {bar_count} bars'
            'ending {end}'.format(
                num_candles=num_candles,
                bar_count=bar_count,
                end=end_dt
            )
        )
        self._write(data, writer, data_frequency)

        return data

    def download_bundle(self, name):
        """

        :param name:
        :return:
        """

    def ingest_ctable(self, asset, data_frequency, period, start_dt, end_dt,
                      writer, empty_rows_behavior='strip', cleanup=False):
        """
        Merge a ctable bundle chunk into the main bundle for the exchange.

        :param asset: TradingPair
        :param data_frequency: str
        :param period: str
        :param writer:
        :param empty_rows_behavior: str
            Ensure that the bundle does not have any missing data.

        :param cleanup: bool
            Remove the temp bundle directory after ingestion.

        :return:
        """

        path = get_bcolz_chunk(
            exchange_name=self.exchange.name,
            symbol=asset.symbol,
            data_frequency=data_frequency,
            period=period
        )

        periods = self.calendar.minutes_in_range(start_dt, end_dt) \
            if data_frequency == 'minute' \
            else self.calendar.sessions_in_range(start_dt, end_dt)

        reader = self.get_reader(data_frequency, path=path)
        arrays = reader.load_raw_arrays(
            sids=[asset.sid],
            fields=['open', 'high', 'low', 'close', 'volume'],
            start_dt=start_dt,
            end_dt=end_dt
        )

        if not arrays:
            return path

        ohlcv = dict(
            open=arrays[0].flatten(),
            high=arrays[1].flatten(),
            low=arrays[2].flatten(),
            close=arrays[3].flatten(),
            volume=arrays[4].flatten()
        )

        df = pd.DataFrame(
            data=ohlcv,
            index=periods
        )

        if empty_rows_behavior is not 'ignore':
            nan_rows = df[df.isnull().T.any().T].index

            if len(nan_rows) > 0:
                dates = []
                previous_date = None
                for row_date in nan_rows.values:
                    row_date = pd.to_datetime(row_date)

                    if previous_date is None:
                        dates.append(row_date)

                    else:
                        seq_date = previous_date + get_delta(1, data_frequency)

                        if row_date > seq_date:
                            dates.append(previous_date)
                            dates.append(row_date)

                    previous_date = row_date

                dates.append(pd.to_datetime(nan_rows.values[-1]))

                name = path.split('/')[-1]
                if empty_rows_behavior == 'warn':
                    log.warn(
                        '\n{name} with end minute {end_minute} has empty rows '
                        'in ranges: {dates}'.format(
                            name=name,
                            end_minute=asset.end_minute,
                            dates=dates
                        )
                    )

                elif empty_rows_behavior == 'raise':
                    raise EmptyValuesInBundleError(
                        name=name,
                        end_minute=asset.end_minute,
                        dates=dates
                    )
                else:
                    df.dropna(inplace=True)

        data = []
        if not df.empty:
            df.sort_index(inplace=True)
            data.append((asset.sid, df))

        self._write(data, writer, data_frequency)

        if cleanup:
            log.debug('removing bundle folder following '
                      'ingestion: {}'.format(path))
            shutil.rmtree(path)

        return path

    def prepare_chunks(self, assets, data_frequency, start_dt, end_dt):
        """

        :param assets:
        :param data_frequency:
        :param start_dt:
        :param end_dt:
        :return:
        """
        reader = self.get_reader(data_frequency)

        chunks = []
        for asset in assets:
            try:
                asset_start, asset_end = \
                    get_adj_dates(start_dt, end_dt, [asset], data_frequency)

            except PricingDataBeforeTradingError:
                continue

            sessions = get_periods_range(asset_start, asset_end, 'daily')

            periods = []
            dt = sessions[0]
            while dt <= sessions[-1]:
                period = '{}-{:02d}'.format(dt.year, dt.month) \
                    if data_frequency == 'minute' else '{}'.format(dt.year)

                if period not in periods:
                    periods.append(period)

                    # Adjusting the period dates to match the availability
                    # of the trading pair
                    if data_frequency == 'minute':
                        period_start, period_end = get_month_start_end(dt)
                        asset_start_month, _ = get_month_start_end(asset_start)

                        if asset_start_month == period_start \
                                and period_start < asset_start:
                            period_start = asset_start

                        _, asset_end_month = get_month_start_end(asset_end)
                        if asset_end_month == period_end \
                                and period_end > asset_end:
                            period_end = asset_end

                    elif data_frequency == 'daily':
                        period_start, period_end = get_year_start_end(dt)
                        asset_start_year, _ = get_year_start_end(asset_start)

                        if asset_start_year == period_start \
                                and period_start < asset_start:
                            period_start = asset_start

                        _, asset_end_year = get_year_start_end(asset_end)
                        if asset_end_year == period_end \
                                and period_end > asset_end:
                            period_end = asset_end
                    else:
                        raise InvalidHistoryFrequencyError(
                            frequency=data_frequency
                        )

                    has_data = range_in_bundle(
                        asset, period_start, period_end, reader
                    )

                    if not has_data:
                        log.debug('adding period: {}'.format(period))
                        chunks.append(
                            dict(
                                asset=asset,
                                period_start=period_start,
                                period_end=period_end,
                                period=period
                            )
                        )

                dt += timedelta(days=1)

        chunks.sort(key=lambda chunk: chunk['period_end'])

        return chunks

    def ingest_assets(self, assets, start_dt, end_dt, data_frequency,
                      show_progress=False):
        """
        Determine if data is missing from the bundle and attempt to ingest it.

        :param assets:
        :param start_dt:
        :param end_dt:
        :return:
        """
        writer = self.get_writer(start_dt, end_dt, data_frequency)
        chunks = self.prepare_chunks(
            assets=assets,
            data_frequency=data_frequency,
            start_dt=start_dt,
            end_dt=end_dt
        )
        with maybe_show_progress(
                chunks,
                show_progress,
                label='Fetching {exchange} {frequency} candles: '.format(
                    exchange=self.exchange.name,
                    frequency=data_frequency
                )) as it:
            for chunk in it:
                self.ingest_ctable(
                    asset=chunk['asset'],
                    data_frequency=data_frequency,
                    period=chunk['period'],
                    start_dt=chunk['period_start'],
                    end_dt=chunk['period_end'],
                    writer=writer,
                    empty_rows_behavior='strip'
                )

    def ingest(self, data_frequency, include_symbols=None,
               exclude_symbols=None, start=None, end=None,
               show_progress=True, environ=os.environ):
        """

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
        start_dt, end_dt = get_adj_dates(start, end, assets, data_frequency)

        self.ingest_assets(assets, start_dt, end_dt, data_frequency,
                           show_progress)
