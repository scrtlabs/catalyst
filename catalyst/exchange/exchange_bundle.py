import os
import os
import shutil
from itertools import chain

import pandas as pd
from catalyst.assets._assets import TradingPair
from logbook import Logger
from pandas.tslib import Timestamp
from pytz import UTC
from six import itervalues

from catalyst import get_calendar
from catalyst.constants import LOG_LEVEL
from catalyst.data.minute_bars import BcolzMinuteOverlappingData, \
    BcolzMinuteBarMetadata
from catalyst.exchange.bundle_utils import range_in_bundle, \
    get_bcolz_chunk, get_delta, get_month_start_end, \
    get_year_start_end, get_df_from_arrays, get_start_dt, get_period_label
from catalyst.exchange.exchange_bcolz import BcolzExchangeBarReader, \
    BcolzExchangeBarWriter
from catalyst.exchange.exchange_errors import EmptyValuesInBundleError, \
    TempBundleNotFoundError, \
    NoDataAvailableOnExchange, \
    PricingDataNotLoadedError
from catalyst.exchange.exchange_utils import get_exchange_folder
from catalyst.utils.cli import maybe_show_progress
from catalyst.utils.paths import ensure_directory

log = Logger('exchange_bundle', level=LOG_LEVEL)

BUNDLE_NAME_TEMPLATE = os.path.join('{root}', '{frequency}_bundle')


def _cachpath(symbol, type_):
    return '-'.join([symbol, type_])


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

        Returns
        -------
        BcolzMinuteBarReader | BcolzDailyBarReader

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
            self._readers[path] = None

        return self._readers[path]

    def update_metadata(self, writer, start_dt, end_dt):
        pass

    def get_writer(self, start_dt, end_dt, data_frequency):
        """
        Get a data writer object, either a new object or from cache

        Returns
        -------
        BcolzMinuteBarWriter | BcolzDailyBarWriter

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

        Parameters
        ----------
        assets: list[TradingPair]
            The assets is scope.
        start_dt: datetime
            The chunk start date.
        end_dt: datetime
            The chunk end date.
        data_frequency: str

        Returns
        -------
        list[TradingPair]
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
        try:
            writer.write(
                data=data,
                show_progress=False,
                invalid_data_behavior='raise'
            )
        except BcolzMinuteOverlappingData as e:
            log.debug('chunk already exists: {}'.format(e))
        except Exception as e:
            log.warn('error when writing data: {}, trying again'.format(e))

            # This is workaround, there is an issue with empty
            # session_label when using a newly created writer
            del self._writers[writer._rootdir]

            writer = self.get_writer(writer._start_session,
                                     writer._end_session, data_frequency)
            writer.write(
                data=data,
                show_progress=False,
                invalid_data_behavior='raise'
            )

    def get_calendar_periods_range(self, start_dt, end_dt, data_frequency):
        """
        Get a list of dates for the specified range.

        Parameters
        ----------
        start_dt: datetime
        end_dt: datetime
        data_frequency: str

        Returns
        -------
        list[datetime]

        """
        return self.calendar.minutes_in_range(start_dt, end_dt) \
            if data_frequency == 'minute' \
            else self.calendar.sessions_in_range(start_dt, end_dt)

    def ingest_df(self, ohlcv_df, data_frequency, asset, writer,
                  empty_rows_behavior='strip'):
        """
        Ingest a DataFrame of OHLCV data for a given market.

        Parameters
        ----------
        ohlcv_df: DataFrame
        data_frequency: str
        asset: TradingPair
        writer:
        empty_rows_behavior: str

        """
        if empty_rows_behavior is not 'ignore':
            nan_rows = ohlcv_df[ohlcv_df.isnull().T.any().T].index

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

                name = '{} from {} to {}'.format(
                    asset.symbol, ohlcv_df.index[0], ohlcv_df.index[-1]
                )
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
                    ohlcv_df.dropna(inplace=True)

        data = []
        if not ohlcv_df.empty:
            ohlcv_df.sort_index(inplace=True)
            data.append((asset.sid, ohlcv_df))

        self._write(data, writer, data_frequency)

    def ingest_ctable(self, asset, data_frequency, period,
                      writer, empty_rows_behavior='strip', cleanup=False):
        """
        Merge a ctable bundle chunk into the main bundle for the exchange.

        Parameters
        ----------
        asset: TradingPair
        data_frequency: str
        period: str
        writer:
        empty_rows_behavior: str
            Ensure that the bundle does not have any missing data.

        cleanup: bool
            Remove the temp bundle directory after ingestion.

        :return:
        """

        path = get_bcolz_chunk(
            exchange_name=self.exchange.name,
            symbol=asset.symbol,
            data_frequency=data_frequency,
            period=period
        )

        reader = self.get_reader(data_frequency, path=path)
        if reader is None:
            raise TempBundleNotFoundError(path=path)

        start_dt = reader.first_trading_day
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

        if not arrays:
            return path

        periods = self.get_calendar_periods_range(
            start_dt, end_dt, data_frequency
        )
        df = get_df_from_arrays(arrays, periods)
        self.ingest_df(
            ohlcv_df=df,
            data_frequency=data_frequency,
            asset=asset,
            writer=writer,
            empty_rows_behavior=empty_rows_behavior
        )

        if cleanup:
            log.debug(
                'removing bundle folder following ingestion: {}'.format(path)
            )
            shutil.rmtree(path)

        return path

    def get_adj_dates(self, start, end, assets, data_frequency):
        """
        Contains a date range to the trading availability of the specified
        markets.

        Parameters
        ----------
        start: datetime
        end: datetime
        assets: list[TradingPair]
        data_frequency: str

        Returns
        -------
        datetime, datetime
        """
        earliest_trade = None
        last_entry = None
        for asset in assets:
            if earliest_trade is None or earliest_trade > asset.start_date:
                if asset.start_date >= self.calendar.first_session:
                    earliest_trade = asset.start_date

                else:
                    earliest_trade = self.calendar.first_session

            end_asset = asset.end_minute if data_frequency == 'minute' else \
                asset.end_daily
            if end_asset is not None:
                if last_entry is None or end_asset > last_entry:
                    last_entry = end_asset

            else:
                end = None
                last_entry = None

        if start is None or \
                (earliest_trade is not None and earliest_trade > start):
            start = earliest_trade

        if end is None or (last_entry is not None and end > last_entry):
            end = last_entry

        if end is None or start is None or start >= end:
            raise NoDataAvailableOnExchange(
                exchange=asset.exchange.title(),
                symbol=[asset.symbol],
                data_frequency=data_frequency,
            )

        return start, end

    def prepare_chunks(self, assets, data_frequency, start_dt, end_dt):
        """
        Split a price data request into chunks corresponding to individual
        bundles.

        Parameters
        ----------
        assets: list[TradingPair]
        data_frequency: str
        start_dt: datetime
        end_dt: datetime

        Returns
        -------
        dict[TradingPair, list[dict(str, Object]]]

        """
        get_start_end = get_month_start_end \
            if data_frequency == 'minute' else get_year_start_end

        start_dt, _ = get_start_end(start_dt)
        _, end_dt = get_start_end(end_dt)

        reader = self.get_reader(data_frequency)

        chunks = dict()
        for asset in assets:
            try:
                # Checking if the the asset has price data in the specified
                # date range
                adj_start, adj_end = self.get_adj_dates(
                    start_dt, end_dt, [asset], data_frequency
                )

            except NoDataAvailableOnExchange as e:
                # If not, we continue to the next asset
                log.debug('skipping {}: {}'.format(asset.symbol, e))
                continue

            dates = pd.date_range(
                start=get_period_label(adj_start, data_frequency),
                end=get_period_label(adj_end, data_frequency),
                freq='MS' if data_frequency == 'minute' else 'AS',
                tz=UTC
            )

            # Adjusting the last date of the range to avoid
            # going over the asset's trading bounds
            dates.values[0] = adj_start
            dates.values[-1] = adj_end

            chunks[asset] = []
            for index, dt in enumerate(dates):

                period_start, period_end = get_start_end(
                    dt=dt,
                    first_day=dt if index == 0 else None,
                    last_day=dt if index == len(dates) - 1 else None
                )

                # Currencies don't always start trading at midnight.
                # Checking the last minute of the day instead.
                range_start = period_start.replace(hour=23, minute=59) \
                    if data_frequency == 'minute' else period_start

                # Checking if the data already exists in the bundle
                # for the date range of the chunk. If not, we create
                # a chunk for ingestion.
                has_data = range_in_bundle(
                    asset, range_start, period_end, reader
                )
                if not has_data:
                    chunks[asset].append(
                        dict(
                            asset=asset,
                            period_start=period_start,
                            period_end=period_end,
                            period=get_period_label(dt, data_frequency)
                        )
                    )

            # We sort the chunks by end date to ingest most recent data first
            chunks[asset].sort(key=lambda chunk: chunk['period_end'])

        return chunks

    def ingest_assets(self, assets, data_frequency, start_dt=None, end_dt=None,
                      show_progress=False, asset_chunks=False):
        """
        Determine if data is missing from the bundle and attempt to ingest it.

        Parameters
        ----------
        assets: list[TradingPair]
        start_dt: datetime
        end_dt: datetime

        """

        if start_dt is None:
            start_dt = self.calendar.first_session

        if end_dt is None:
            end_dt = pd.Timestamp.utcnow()

        start_dt, end_dt = self.get_adj_dates(
            start_dt, end_dt, assets, data_frequency
        )
        chunks = self.prepare_chunks(
            assets=assets,
            data_frequency=data_frequency,
            start_dt=start_dt,
            end_dt=end_dt
        )

        # Since chunks are either monthly or yearly, it is possible that
        # our ingestion data range is greater than specified. We adjust
        # the boundaries to ensure that the writer can write all data.
        all_chunks = list(chain.from_iterable(itervalues(chunks)))
        for chunk in all_chunks:
            if chunk['period_start'] < start_dt:
                start_dt = chunk['period_start']

            if chunk['period_end'] > end_dt:
                end_dt = chunk['period_end']

        writer = self.get_writer(start_dt, end_dt, data_frequency)

        if asset_chunks:
            for asset in chunks:
                with maybe_show_progress(
                        chunks[asset],
                        show_progress,
                        label='Ingesting {frequency} price data for '
                              '{symbol} on {exchange}'.format(
                            exchange=self.exchange.name,
                            frequency=data_frequency,
                            symbol=asset.symbol
                        )) as it:
                    for chunk in it:
                        self.ingest_ctable(
                            asset=chunk['asset'],
                            data_frequency=data_frequency,
                            period=chunk['period'],
                            writer=writer,
                            empty_rows_behavior='strip',
                            cleanup=True
                        )
        else:
            with maybe_show_progress(
                    all_chunks,
                    show_progress,
                    label='Ingesting {frequency} price data on '
                          '{exchange}'.format(
                        exchange=self.exchange.name,
                        frequency=data_frequency,
                    )) as it:
                for chunk in it:
                    self.ingest_ctable(
                        asset=chunk['asset'],
                        data_frequency=data_frequency,
                        period=chunk['period'],
                        writer=writer,
                        empty_rows_behavior='strip',
                        cleanup=True
                    )

    def ingest(self, data_frequency, include_symbols=None,
               exclude_symbols=None, start=None, end=None,
               show_progress=True, environ=os.environ):
        """
        Inject data based on specified parameters.

        Parameters
        ----------
        data_frequency: str
        include_symbols: str
        exclude_symbols: str
        start: datetime
        end: datetime
        show_progress: bool
        environ:

        """
        assets = self.get_assets(include_symbols, exclude_symbols)

        for frequency in data_frequency.split(','):
            self.ingest_assets(assets, frequency, start, end,
                               show_progress)

    def get_history_window_series_and_load(self,
                                           assets,  # type: List[TradingPair]
                                           end_dt,  # type: Timestamp
                                           bar_count,  # type: int
                                           field,  # type: str
                                           data_frequency,  # type: str
                                           algo_end_dt=None  # type: Timestamp
                                           ):
        """
        Retrieve price data history, ingest missing data.

        Parameters
        ----------
        assets: list[TradingPair]
        end_dt: datetime
        bar_count: int
        field: str
        data_frequency: str
        algo_end_dt: datetime

        Returns
        -------
        Series

        """
        try:
            series = self.get_history_window_series(
                assets=assets,
                end_dt=end_dt,
                bar_count=bar_count,
                field=field,
                data_frequency=data_frequency
            )
            return pd.DataFrame(series)

        except PricingDataNotLoadedError:
            start_dt = get_start_dt(end_dt, bar_count, data_frequency)
            log.info(
                'pricing data for {symbol} not found in range '
                '{start} to {end}, updating the bundles.'.format(
                    symbol=[asset.symbol for asset in assets],
                    start=start_dt,
                    end=end_dt
                )
            )
            self.ingest_assets(
                assets=assets,
                start_dt=start_dt,
                end_dt=algo_end_dt,
                data_frequency=data_frequency,
                show_progress=True,
                asset_chunks=True
            )
            series = self.get_history_window_series(
                assets=assets,
                end_dt=end_dt,
                bar_count=bar_count,
                field=field,
                data_frequency=data_frequency,
                reset_reader=False
            )
            return series

    def get_spot_values(self,
                        assets,  # type: List[TradingPair]
                        field,  # type: str
                        dt,  # type: Timestamp
                        data_frequency,  # type: str
                        reset_reader=False  # type: bool
                        ):
        # type: (...) -> List[float]
        """
        The spot values for the gives assets, field and date. Reads from
        the exchange data bundle.

        :param assets:
        :param field:
        :param dt:
        :param data_frequency:
        :param reset_reader:
        :return:
        """
        values = []
        try:
            reader = self.get_reader(data_frequency)
            if reset_reader:
                del self._readers[reader._rootdir]
                reader = self.get_reader(data_frequency)

            for asset in assets:
                value = reader.get_value(
                    sid=asset.sid,
                    dt=dt,
                    field=field
                )
                values.append(value)

            return values

        except Exception:
            symbols = [asset.symbol for asset in assets]
            raise PricingDataNotLoadedError(
                field=field,
                first_trading_day=min([asset.start_date for asset in assets]),
                exchange=self.exchange.name,
                symbols=symbols,
                symbol_list=','.join(symbols),
                data_frequency=data_frequency
            )

    def get_history_window_series(self,
                                  assets,
                                  end_dt,
                                  bar_count,
                                  field,
                                  data_frequency,
                                  reset_reader=False):
        start_dt = get_start_dt(end_dt, bar_count, data_frequency)
        start_dt, end_dt = self.get_adj_dates(
            start_dt, end_dt, assets, data_frequency
        )

        reader = self.get_reader(data_frequency)
        if reset_reader:
            del self._readers[reader._rootdir]
            reader = self.get_reader(data_frequency)

        if reader is None:
            symbols = [asset.symbol for asset in assets]
            raise PricingDataNotLoadedError(
                field=field,
                first_trading_day=min([asset.start_date for asset in assets]),
                exchange=self.exchange.name,
                symbols=symbols,
                symbol_list=','.join(symbols),
                data_frequency=data_frequency
            )

        for asset in assets:
            asset_start_dt, asset_end_dt = self.get_adj_dates(
                start_dt, end_dt, assets, data_frequency
            )

            in_bundle = range_in_bundle(
                asset, asset_start_dt, asset_end_dt, reader
            )
            if not in_bundle:
                raise PricingDataNotLoadedError(
                    field=field,
                    first_trading_day=asset.start_date,
                    exchange=self.exchange.name,
                    symbols=asset.symbol,
                    symbol_list=asset.symbol,
                    data_frequency=data_frequency
                )

        series = dict()
        try:
            arrays = reader.load_raw_arrays(
                sids=[asset.sid for asset in assets],
                fields=[field],
                start_dt=start_dt,
                end_dt=end_dt
            )

        except Exception:
            symbols = [asset.symbol.encode('utf-8') for asset in assets]
            raise PricingDataNotLoadedError(
                field=field,
                first_trading_day=min([asset.start_date for asset in assets]),
                exchange=self.exchange.name,
                symbols=symbols,
                symbol_list=','.join(symbols),
                data_frequency=data_frequency
            )

        periods = self.get_calendar_periods_range(
            start_dt, end_dt, data_frequency
        )

        for asset_index, asset in enumerate(assets):
            asset_values = arrays[asset_index]

            value_series = pd.Series(asset_values.flatten(), index=periods)
            series[asset] = value_series

        return series

    def clean(self, data_frequency):
        log.debug('cleaning exchange {}, frequency {}'.format(
            self.exchange.name, data_frequency
        ))
        root = get_exchange_folder(self.exchange.name)

        symbols = os.path.join(root, 'symbols.json')
        if os.path.isfile(symbols):
            os.remove(symbols)

        temp_bundles = os.path.join(root, 'temp_bundles')

        if os.path.isdir(temp_bundles):
            log.debug('removing folder and content: {}'.format(temp_bundles))
            shutil.rmtree(temp_bundles)
            log.debug('{} removed'.format(temp_bundles))

        frequencies = ['daily', 'minute'] if data_frequency is None \
            else [data_frequency]

        for frequency in frequencies:
            label = '{}_bundle'.format(frequency)
            frequency_bundle = os.path.join(root, label)

            if os.path.isdir(frequency_bundle):
                log.debug(
                    'removing folder and content: {}'.format(frequency_bundle)
                )
                shutil.rmtree(frequency_bundle)
                log.debug('{} removed'.format(frequency_bundle))
