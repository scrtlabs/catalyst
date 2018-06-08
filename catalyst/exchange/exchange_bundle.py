import os
import shutil
from datetime import timedelta
from functools import partial
from itertools import chain
from operator import is_not

import numpy as np
import pandas as pd
import pytz
from catalyst import get_calendar
from catalyst.assets._assets import TradingPair
from catalyst.constants import DATE_TIME_FORMAT, AUTO_INGEST
from catalyst.constants import LOG_LEVEL
from catalyst.data.minute_bars import BcolzMinuteOverlappingData, \
    BcolzMinuteBarMetadata
from catalyst.exchange.exchange_bcolz import BcolzExchangeBarReader, \
    BcolzExchangeBarWriter
from catalyst.exchange.exchange_errors import EmptyValuesInBundleError, \
    TempBundleNotFoundError, \
    NoDataAvailableOnExchange, \
    PricingDataNotLoadedError, DataCorruptionError, PricingDataValueError
from catalyst.exchange.utils.bundle_utils import range_in_bundle, \
    get_bcolz_chunk, get_df_from_arrays, get_assets
from catalyst.exchange.utils.datetime_utils import get_start_dt, \
    get_period_label, get_month_start_end, get_year_start_end
from catalyst.exchange.utils.exchange_utils import get_exchange_folder, \
    save_exchange_symbols, mixin_market_params, get_catalyst_symbol
from catalyst.utils.cli import maybe_show_progress
from catalyst.utils.paths import ensure_directory
from logbook import Logger
from pytz import UTC
from six import itervalues

log = Logger('exchange_bundle', level=LOG_LEVEL)

BUNDLE_NAME_TEMPLATE = os.path.join('{root}', '{frequency}_bundle')


def _cachpath(symbol, type_):
    return '-'.join([symbol, type_])


class ExchangeBundle:
    def __init__(self, exchange_name):
        self.exchange_name = exchange_name
        self.minutes_per_day = 1440
        self.default_ohlc_ratio = 1000000
        self._writers = dict()
        self._readers = dict()
        self.calendar = get_calendar('OPEN')
        self.exchange = None

    def get_reader(self, data_frequency, path=None):
        """
        Get a data writer object, either a new object or from cache

        Returns
        -------
        BcolzMinuteBarReader | BcolzDailyBarReader

        """
        if path is None:
            root = get_exchange_folder(self.exchange_name)
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
        root = get_exchange_folder(self.exchange_name)
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
        start_dt: pd.Timestamp
            The chunk start date.
        end_dt: pd.Timestamp
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
        start_dt: pd.Timestamp
        end_dt: pd.Timestamp
        data_frequency: str

        Returns
        -------
        list[datetime]

        """
        return self.calendar.minutes_in_range(start_dt, end_dt) \
            if data_frequency == 'minute' \
            else self.calendar.sessions_in_range(start_dt, end_dt)

    def _spot_empty_periods(self, ohlcv_df, asset, data_frequency,
                            empty_rows_behavior):
        problems = []

        nan_rows = ohlcv_df[ohlcv_df.isnull().T.any().T].index
        if len(nan_rows) > 0:
            dates = []
            for row_date in nan_rows.values:
                row_date = pd.to_datetime(row_date, utc=True)
                if row_date > asset.start_date:
                    dates.append(row_date)

            if len(dates) > 0:
                end_dt = asset.end_minute if data_frequency == 'minute' \
                    else asset.end_daily

                problem = '{name} ({start_dt} to {end_dt}) has empty ' \
                          'periods: {dates}'.format(
                                name=asset.symbol,
                                start_dt=asset.start_date.strftime(
                                    DATE_TIME_FORMAT),
                                end_dt=end_dt.strftime(DATE_TIME_FORMAT),
                                dates=[date.strftime(
                                    DATE_TIME_FORMAT) for date in dates])

                if empty_rows_behavior == 'warn':
                    log.warn(problem)

                elif empty_rows_behavior == 'raise':
                    raise EmptyValuesInBundleError(
                        name=asset.symbol,
                        end_minute=end_dt,
                        dates=dates, )

                else:
                    ohlcv_df.dropna(inplace=True)

            else:
                problem = None

            problems.append(problem)

        return problems

    def _spot_duplicates(self, ohlcv_df, asset, data_frequency, threshold):
        # TODO: work in progress
        series = ohlcv_df.reset_index().groupby('close')['index'].apply(
            np.array
        )

        ref_delta = timedelta(minutes=1) if data_frequency == 'minute' \
            else timedelta(days=1)

        dups = series.loc[lambda values: [len(x) > 10 for x in values]]

        for index, dates in dups.iteritems():
            prev_date = None
            for date in dates:
                if prev_date is not None:
                    delta = (date - prev_date) / 1e9
                    if delta == ref_delta.seconds:
                        log.info('pex')

                prev_date = date

        problems = []
        for index, dates in dups.iteritems():
            end_dt = asset.end_minute if data_frequency == 'minute' \
                else asset.end_daily

            problem = '{name} ({start_dt} to {end_dt}) has {threshold} ' \
                      'identical close values on: {dates}'.format(
                        name=asset.symbol,
                        start_dt=asset.start_date.strftime(DATE_TIME_FORMAT),
                        end_dt=end_dt.strftime(DATE_TIME_FORMAT),
                        threshold=threshold,
                        dates=[pd.to_datetime(date).strftime(DATE_TIME_FORMAT)
                               for date in dates])

            problems.append(problem)

        return problems

    def ingest_df(self, ohlcv_df, data_frequency, asset, writer,
                  empty_rows_behavior='warn', duplicates_threshold=None):
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
        problems = []
        if empty_rows_behavior is not 'ignore':
            problems += self._spot_empty_periods(
                ohlcv_df, asset, data_frequency, empty_rows_behavior
            )

        # if duplicates_threshold is not None:
        #     problems += self._spot_duplicates(
        #         ohlcv_df, asset, data_frequency, duplicates_threshold
        #     )

        data = []
        if not ohlcv_df.empty:
            ohlcv_df.sort_index(inplace=True)
            data.append((asset.sid, ohlcv_df))

        self._write(data, writer, data_frequency)

        return problems

    def ingest_ctable(self, asset, data_frequency, period,
                      writer, empty_rows_behavior='strip',
                      duplicates_threshold=100, cleanup=False):
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

        Returns
        -------
        list[str]
            A list of problems which occurred during ingestion.

        """
        problems = []

        # Download and extract the bundle
        path = get_bcolz_chunk(
            exchange_name=self.exchange_name,
            symbol=asset.symbol,
            data_frequency=data_frequency,
            period=period
        )

        reader = self.get_reader(data_frequency, path=path)
        if reader is None:
            try:
                log.warn('the reader is unable to use bundle: {}, '
                         'deleting it.'.format(path))
                shutil.rmtree(path)

            except Exception as e:
                log.warn('unable to remove temp bundle: {}'.format(e))

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
            return reader._rootdir

        periods = self.get_calendar_periods_range(
            start_dt, end_dt, data_frequency
        )
        df = get_df_from_arrays(arrays, periods)
        problems += self.ingest_df(
            ohlcv_df=df,
            data_frequency=data_frequency,
            asset=asset,
            writer=writer,
            empty_rows_behavior=empty_rows_behavior,
            duplicates_threshold=duplicates_threshold
        )

        if cleanup:
            log.debug(
                'removing bundle folder following ingestion: {}'.format(
                    reader._rootdir)
            )
            shutil.rmtree(reader._rootdir)

        return filter(partial(is_not, None), problems)

    def get_adj_dates(self, start, end, assets, data_frequency):
        """
        Contains a date range to the trading availability of the specified
        markets.

        Parameters
        ----------
        start: pd.Timestamp
        end: pd.Timestamp
        assets: list[TradingPair]
        data_frequency: str

        Returns
        -------
        pd.Timestamp, pd.Timestamp
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

        if last_entry is not None and (end is None or end > last_entry):
            end = last_entry.replace(minute=59, hour=23) \
                if data_frequency == 'minute' else last_entry

        if end is None or start is None or start > end:
            raise NoDataAvailableOnExchange(
                exchange=[asset.exchange for asset in assets],
                symbol=[asset.symbol for asset in assets],
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
        start_dt: pd.Timestamp
        end_dt: pd.Timestamp

        Returns
        -------
        dict[TradingPair, list[dict(str, Object]]]

        """
        get_start_end = get_month_start_end \
            if data_frequency == 'minute' else get_year_start_end

        # Get a reader for the main bundle to verify if data exists
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
                    period = get_period_label(dt, data_frequency)
                    chunk = dict(
                        asset=asset,
                        period=period,
                    )
                    chunks[asset].append(chunk)

            # We sort the chunks by end date to ingest most recent data first
            chunks[asset].sort(
                key=lambda chunk: pd.to_datetime(chunk['period'])
            )

        return chunks

    def ingest_assets(self, assets, data_frequency, start_dt=None, end_dt=None,
                      show_progress=False, show_breakdown=False,
                      show_report=False):
        """
        Determine if data is missing from the bundle and attempt to ingest it.

        Parameters
        ----------
        assets: list[TradingPair]
        data_frequency: str
        start_dt: pd.Timestamp
        end_dt: pd.Timestamp
        show_progress: bool
        show_breakdown: bool

        """
        if start_dt is None:
            start_dt = self.calendar.first_session

        if end_dt is None:
            end_dt = pd.Timestamp.utcnow()

        get_start_end = get_month_start_end \
            if data_frequency == 'minute' else get_year_start_end

        # Assign the first and last day of the period
        start_dt, _ = get_start_end(start_dt)
        _, end_dt = get_start_end(end_dt)

        chunks = self.prepare_chunks(
            assets=assets,
            data_frequency=data_frequency,
            start_dt=start_dt,
            end_dt=end_dt
        )

        problems = []
        # This is the common writer for the entire exchange bundle
        # we want to give an end_date far in time
        writer = self.get_writer(start_dt, end_dt, data_frequency)
        if show_breakdown:
            if chunks:
                for asset in chunks:
                    with maybe_show_progress(
                        chunks[asset],
                        show_progress,
                        label='Ingesting {frequency} price data for '
                              '{symbol} on {exchange}'.format(
                            exchange=self.exchange_name,
                            frequency=data_frequency,
                            symbol=asset.symbol
                            )) as it:
                        for chunk in it:
                            problems += self.ingest_ctable(
                                asset=chunk['asset'],
                                data_frequency=data_frequency,
                                period=chunk['period'],
                                writer=writer,
                                empty_rows_behavior='strip',
                                cleanup=True
                            )
        else:
            all_chunks = list(chain.from_iterable(itervalues(chunks)))
            # We sort the chunks by end date to ingest most recent data first
            if all_chunks:
                all_chunks.sort(
                    key=lambda chunk: pd.to_datetime(chunk['period'])
                )
                with maybe_show_progress(
                    all_chunks,
                    show_progress,
                    label='Ingesting {frequency} price data on '
                          '{exchange}'.format(
                        exchange=self.exchange_name,
                        frequency=data_frequency,
                        )) as it:
                    for chunk in it:
                        problems += self.ingest_ctable(
                            asset=chunk['asset'],
                            data_frequency=data_frequency,
                            period=chunk['period'],
                            writer=writer,
                            empty_rows_behavior='strip',
                            cleanup=True
                        )

        if show_report and len(problems) > 0:
            log.info('problems during ingestion:{}\n'.format(
                '\n'.join(problems)
            ))

    def ingest_csv(self, path, data_frequency, empty_rows_behavior='strip',
                   duplicates_threshold=100):
        """
        Ingest price data from a CSV file.

        Parameters
        ----------
        path: str
        data_frequency: str

        Returns
        -------
        list[str]
            A list of potential problems detected during ingestion.

        """
        log.info('ingesting csv file: {}'.format(path))

        if self.exchange is None:
            # Avoid circular dependencies
            from catalyst.exchange.utils.factory import get_exchange
            self.exchange = get_exchange(self.exchange_name)

        problems = []
        df = pd.read_csv(
            path,
            header=0,
            sep=',',
            dtype=dict(
                symbol=np.object_,
                last_traded=np.object_,
                open=np.float64,
                high=np.float64,
                low=np.float64,
                close=np.float64,
                volume=np.float64
            ),
            parse_dates=['last_traded'],
            index_col=None
        )
        min_start_dt = None
        max_end_dt = None

        symbols = df['symbol'].unique()

        # Apply the timezone before creating an index for simplicity
        df['last_traded'] = df['last_traded'].dt.tz_localize(pytz.UTC)
        df.set_index(['symbol', 'last_traded'], drop=True, inplace=True)

        assets = dict()
        for symbol in symbols:
            start_dt = df.index.get_level_values(1).min()
            end_dt = df.index.get_level_values(1).max()
            end_dt_key = 'end_{}'.format(data_frequency)

            market = self.exchange.get_market(symbol)
            if market is None:
                raise ValueError('symbol not available in the exchange.')

            params = dict(
                exchange=self.exchange.name,
                data_source='local',
                exchange_symbol=market['id'],
            )
            mixin_market_params(self.exchange_name, params, market)

            asset_def = self.exchange.get_asset_def(market, True)
            if asset_def is not None:
                params['symbol'] = asset_def['symbol']

                params['start_date'] = asset_def['start_date'] \
                    if asset_def['start_date'] < start_dt else start_dt

                params['end_date'] = asset_def[end_dt_key] \
                    if asset_def[end_dt_key] > end_dt else end_dt

                params['end_daily'] = end_dt \
                    if data_frequency == 'daily' else asset_def['end_daily']

                params['end_minute'] = end_dt \
                    if data_frequency == 'minute' else asset_def['end_minute']

            else:
                params['symbol'] = get_catalyst_symbol(market)

                params['end_daily'] = end_dt \
                    if data_frequency == 'daily' else 'N/A'
                params['end_minute'] = end_dt \
                    if data_frequency == 'minute' else 'N/A'

            if min_start_dt is None or start_dt < min_start_dt:
                min_start_dt = start_dt

            if max_end_dt is None or end_dt > max_end_dt:
                max_end_dt = end_dt

            asset = TradingPair(**params)
            assets[market['id']] = asset

        save_exchange_symbols(self.exchange_name, assets, True)

        writer = self.get_writer(
            start_dt=min_start_dt.replace(hour=00, minute=00),
            end_dt=max_end_dt.replace(hour=23, minute=59),
            data_frequency=data_frequency
        )

        for symbol in assets:
            # here the symbol is the market['id']
            asset = assets[symbol]
            ohlcv_df = df.loc[
                (df.index.get_level_values(0) == asset.symbol)
            ]  # type: pd.DataFrame
            ohlcv_df.index = ohlcv_df.index.droplevel(0)

            period_start = start_dt.replace(hour=00, minute=00)
            period_end = end_dt.replace(hour=23, minute=59)
            periods = self.get_calendar_periods_range(
                period_start, period_end, data_frequency
            )

            # We're not really resampling but ensuring that each frame
            # contains data
            ohlcv_df = ohlcv_df.reindex(periods, method='ffill')
            ohlcv_df['volume'] = ohlcv_df['volume'].fillna(0)

            problems += self.ingest_df(
                ohlcv_df=ohlcv_df,
                data_frequency=data_frequency,
                asset=asset,
                writer=writer,
                empty_rows_behavior=empty_rows_behavior,
                duplicates_threshold=duplicates_threshold
            )
        return filter(partial(is_not, None), problems)

    def ingest(self, data_frequency, include_symbols=None,
               exclude_symbols=None, start=None, end=None, csv=None,
               show_progress=True, show_breakdown=True, show_report=True):
        """
        Inject data based on specified parameters.

        Parameters
        ----------
        data_frequency: str
        include_symbols: str
        exclude_symbols: str
        start: pd.Timestamp
        end: pd.Timestamp
        show_progress: bool
        environ:

        """
        if csv is not None:
            self.ingest_csv(csv, data_frequency)

        else:
            if self.exchange is None:
                # Avoid circular dependencies
                from catalyst.exchange.utils.factory import get_exchange
                self.exchange = get_exchange(self.exchange_name)

            assets = get_assets(
                self.exchange, include_symbols, exclude_symbols
            )
            for frequency in data_frequency.split(','):
                self.ingest_assets(
                    assets=assets,
                    data_frequency=frequency,
                    start_dt=start,
                    end_dt=end,
                    show_progress=show_progress,
                    show_breakdown=show_breakdown,
                    show_report=show_report
                )

    def get_history_window_series_and_load(self,
                                           assets,
                                           end_dt,
                                           bar_count,
                                           field,
                                           data_frequency,
                                           algo_end_dt=None,
                                           force_auto_ingest=False
                                           ):
        """
        Retrieve price data history, ingest missing data.

        Parameters
        ----------
        assets: list[TradingPair]
        end_dt: pd.Timestamp
        bar_count: int
        field: str
        data_frequency: str
        algo_end_dt: pd.Timestamp

        Returns
        -------
        Series

        """
        if AUTO_INGEST or force_auto_ingest:
            try:
                series = self.get_history_window_series(
                    assets=assets,
                    end_dt=end_dt,
                    bar_count=bar_count,
                    field=field,
                    data_frequency=data_frequency,
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
                    end_dt=algo_end_dt,  # TODO: apply trailing bars
                    data_frequency=data_frequency,
                    show_progress=True,
                    show_breakdown=True
                )
                series = self.get_history_window_series(
                    assets=assets,
                    end_dt=end_dt,
                    bar_count=bar_count,
                    field=field,
                    data_frequency=data_frequency,
                    reset_reader=True,
                )
                return series

        else:
            series = self.get_history_window_series(
                assets=assets,
                end_dt=end_dt,
                bar_count=bar_count,
                field=field,
                data_frequency=data_frequency,
            )
            return pd.DataFrame(series)

    def get_spot_values(self,
                        assets,
                        field,
                        dt,
                        data_frequency,
                        reset_reader=False
                        ):
        """
        The spot values for the gives assets, field and date. Reads from
        the exchange data bundle.

        Parameters
        ----------
        assets: list[TradingPair]
        field: str
        dt: pd.Timestamp
        data_frequency: str
        reset_reader:

        Returns
        -------
        float

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
                exchange=self.exchange_name,
                symbols=symbols,
                symbol_list=','.join(symbols),
                data_frequency=data_frequency,
                start_dt=dt,
                end_dt=dt
            )

    def get_history_window_series(self,
                                  assets,
                                  end_dt,
                                  bar_count,
                                  field,
                                  data_frequency,
                                  reset_reader=False):
        start_dt = get_start_dt(end_dt, bar_count, data_frequency, False)
        start_dt, _ = self.get_adj_dates(
            start_dt, end_dt, assets, data_frequency
        )

        # This is an attempt to resolve some caching with the reader
        # when auto-ingesting data.
        # TODO: needs more work
        reader = self.get_reader(data_frequency)
        if reset_reader:
            del self._readers[reader._rootdir]
            reader = self.get_reader(data_frequency)

        if reader is None:
            symbols = [asset.symbol for asset in assets]
            raise PricingDataNotLoadedError(
                field=field,
                first_trading_day=min([asset.start_date for asset in assets]),
                exchange=self.exchange_name,
                symbols=symbols,
                symbol_list=','.join(symbols),
                data_frequency=data_frequency,
                start_dt=start_dt,
                end_dt=end_dt
            )

        series = dict()
        for asset in assets:
            asset_start_dt, _ = self.get_adj_dates(
                start_dt, end_dt, assets, data_frequency
            )
            in_bundle = range_in_bundle(
                asset, asset_start_dt, end_dt, reader
            )
            if not in_bundle:
                raise PricingDataNotLoadedError(
                    field=field,
                    first_trading_day=asset.start_date,
                    exchange=self.exchange_name,
                    symbols=asset.symbol,
                    symbol_list=asset.symbol,
                    data_frequency=data_frequency,
                    start_dt=asset_start_dt,
                    end_dt=end_dt
                )

            periods = self.get_calendar_periods_range(
                asset_start_dt, end_dt, data_frequency
            )
            # This does not behave well when requesting multiple assets
            # when the start or end date of one asset is outside of the range
            # looking at the logic in load_raw_arrays(), we are not achieving
            # any performance gain by requesting multiple sids at once. It's
            # looping through the sids and making separate requests anyway.
            arrays = reader.load_raw_arrays(
                sids=[asset.sid],
                fields=[field],
                start_dt=start_dt,
                end_dt=end_dt
            )
            if len(arrays) == 0:
                raise DataCorruptionError(
                    exchange=self.exchange_name,
                    symbols=asset.symbol,
                    start_dt=asset_start_dt,
                    end_dt=end_dt
                )

            field_values = arrays[0][:, 0]

            try:
                value_series = pd.Series(field_values, index=periods)
                series[asset] = value_series
            except ValueError as e:
                raise PricingDataValueError(
                    exchange=asset.exchange,
                    symbol=asset.symbol,
                    start_dt=asset_start_dt,
                    end_dt=end_dt,
                    error=e
                )

        return series

    def clean(self, data_frequency):
        """
        Removing the bundle data from the catalyst folder.

        Parameters
        ----------
        data_frequency: str

        """
        log.debug('cleaning exchange {}, frequency {}'.format(
            self.exchange_name, data_frequency
        ))
        root = get_exchange_folder(self.exchange_name)

        symbols = os.path.join(root, 'symbols.json')
        if os.path.isfile(symbols):
            os.remove(symbols)

        local_symbols = os.path.join(root, 'symbols_local.json')
        if os.path.isfile(local_symbols):
            os.remove(local_symbols)

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
