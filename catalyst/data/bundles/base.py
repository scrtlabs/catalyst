#
# Copyright 2017 Enigma MPC, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from itertools import count
import tarfile
from time import sleep

from abc import abstractmethod, abstractproperty
import logbook
import pandas as pd

from . import core as bundles

from catalyst.utils.cli import (
    item_show_count,
    maybe_show_progress
)
from catalyst.utils.memoize import lazyval

from catalyst.constants import LOG_LEVEL

logbook.StderrHandler().push_application()
log = logbook.Logger(__name__, level=LOG_LEVEL)

DEFAULT_RETRIES = 5


class BaseBundle(object):
    def __init__(self, asset_filter=[]):
        self._asset_filter = asset_filter
        self._reset()

    def _reset(self):
        self._splits = []
        self._dividends = []

    @lazyval
    def name(self):
        raise NotImplementedError()

    @lazyval
    def exchange(self):
        raise NotImplementedError()

    @lazyval
    def calendar_name(self):
        raise NotImplementedError()

    @lazyval
    def minutes_per_day(self):
        raise NotImplementedError()

    @lazyval
    def frequencies(self):
        raise NotImplementedError()

    @lazyval
    def md_column_names(self):
        return _dtypes_to_cols(self.md_dtypes)

    @lazyval
    def md_dtypes(self):
        raise NotImplementedError()

    @lazyval
    def column_names(self):
        return _dtypes_to_cols(self.dtypes)

    @lazyval
    def dtypes(self):
        raise NotImplementedError()

    @lazyval
    def tar_url(self):
        raise NotImplementedError()

    @lazyval
    def wait_time(self):
        raise NotImplementedError()

    @abstractproperty
    def splits(self):
        raise NotImplementedError()

    @abstractproperty
    def dividends(self):
        raise NotImplementedError()

    @abstractmethod
    def fetch_raw_metadata_frame(self, api_key, page_number):
        raise NotImplementedError()

    def post_process_symbol_metadata(self, metadata, data):
        return metadata

    @abstractmethod
    def fetch_raw_symbol_frame(self, api_key, symbol, start_date, end_date):
        raise NotImplementedError()

    def ingest(self,
               environ,
               asset_db_writer,
               minute_bar_writer,
               daily_bar_writer,
               adjustment_writer,
               calendar,
               start_session,
               end_session,
               cache,
               show_progress,
               is_compile,
               output_dir):

        try:
            api_key = environ.get('CATALYST_API_KEY')
            retries = environ.get('CATALYST_DOWNLOAD_ATTEMPTS', 5)

            if is_compile:
                # User has instructed local compilation & ingestion of bundle.
                # Fetch raw metadata for all symbols.
                raw_metadata = self._fetch_metadata_frame(
                    api_key,
                    cache=cache,
                    retries=retries,
                    environ=environ,
                    show_progress=show_progress,
                )

                # Compile daily symbol data if bundle supports daily mode and
                # persist the dataset to disk.
                symbol_map = raw_metadata.symbol
                if 'daily' in self.frequencies:
                    daily_bar_writer.write(
                        self._fetch_symbol_iter(
                            api_key,
                            cache,
                            symbol_map,
                            calendar,
                            start_session,
                            end_session,
                            'daily',
                            retries,
                        ),
                        assets=raw_metadata.index,
                        show_progress=show_progress,
                    )

                # Post-process metadata using cached symbol frames, and write
                # to disk.  This metadata must be written before any attempt
                # to write minute data.
                metadata = self._post_process_metadata(
                    raw_metadata,
                    cache,
                    show_progress=show_progress,
                )
                asset_db_writer.write(metadata)

                # Compile minute symbol data if bundle supports minute mode and
                # persist the dataset to disk.
                if 'minute' in self.frequencies:
                    minute_bar_writer.write(
                        self._fetch_symbol_iter(
                            api_key,
                            cache,
                            symbol_map,
                            calendar,
                            start_session,
                            end_session,
                            'minute',
                            retries,
                        ),
                        show_progress=show_progress,
                    )

                # For legacy purposes, this call is required to ensure the
                # database contains an appropriately initialized file
                # structure.  We don't forsee a usecase for adjustments at
                # this time, but may later choose to expose this functionality
                # in the future.
                adjustment_writer.write(
                    splits=(
                        pd.concat(self.splits, ignore_index=True)
                        if len(self.splits) > 0 else
                        None
                    ),
                    dividends=(
                        pd.concat(self.dividends, ignore_index=True)
                        if len(self.dividends) > 0 else
                        None
                    ),
                )
            else:
                # Otherwise, user has instructed to download and untar bundle
                # directly from the bundles `tar_url`.
                self._download_and_untar(show_progress, output_dir)
        except Exception as e:
            log.exception(
                ' Failed to ingest {name}:\n{msg}'.format(
                    name=self.name,
                    msg=str(e),
                )
            )
        else:
            self._reset()

    def _download_and_untar(self, show_progress, output_dir):
        # Download bundle conditioned on whether the user would like progress
        # information to be displayed in the CLI.
        if show_progress:
            data = bundles.download_with_progress(
                self.tar_url,
                chunk_size=bundles.ONE_MEGABYTE,
                label='Downloading {name} bundle'.format(name=self.name),
            )
        else:
            data = bundles.download_without_progress(self.tar_url)

        # File transfer has completed, untar the bundle to the appropriate
        # data directory.
        with tarfile.open('r', fileobj=data) as tar:
            tar.extractall(output_dir)

    def _fetch_metadata_frame(self,
                              api_key,
                              cache,
                              retries=DEFAULT_RETRIES,
                              environ=None,
                              show_progress=False):

        # Setup raw metadata iterator to fetch pages if necessary.
        raw_iter = self._fetch_metadata_iter(api_key, cache, retries, environ)

        # Concatenate all frame in iterator to compute a single metadata frame.
        with maybe_show_progress(
            raw_iter,
            show_progress,
            label='Fetching symbol metadata',
            item_show_func=item_show_count(),
            length=3,
            show_percent=False,
        ) as blocks:
            metadata = pd.concat(blocks, ignore_index=True)

        return metadata

    def _fetch_metadata_iter(self, api_key, cache, retries, environ):
        for page_number in count(1):
            # Attempt to load metadata page from cache.  If it does not exist,
            # poll the API upto `retries` times in order to get raw DataFrame.
            key = 'metadata-page-{pn}.frame'.format(pn=page_number)
            try:
                raw = cache[key]
            except KeyError:
                for _ in range(retries):
                    try:
                        raw = self.fetch_raw_metadata_frame(
                            api_key,
                            page_number,
                        )
                        break
                    except ValueError:
                        raw = pd.DataFrame([])
                        break
                    except Exception:
                        log.exception(
                            'Failed to load metadata from {}. '
                            'Retrying.'.format(self.name)
                        )
                else:
                    raise ValueError(
                        'Failed to download metadata page {} after {} '
                        'attempts.'.format(page_number, retries)
                    )

            if raw.empty:
                # Empty DataFrame signals completion.
                break

            # Apply selective asset filtering, useful for benchmark
            # ingestion.
            if self._asset_filter:
                raw = raw[raw.symbol.isin(self._asset_filter)]

            # Update cached value for key.
            cache[key] = raw

            # Return metadata frame to application.
            yield raw

    def _post_process_metadata(self, metadata, cache, show_progress=False):
        # Create empty data frame using target metadata column names and dtypes
        final_metadata = pd.DataFrame(
            columns=self.md_column_names,
            index=metadata.index,
        )

        # Iterate over the available symbols, loading the asset's raw symbol
        # data from the cache.  The final metadata is computed and recorded in
        # the appropriate row depending on the asset's id.
        with maybe_show_progress(
            metadata.symbol.iteritems(),
            show_progress,
            label='Post-processing symbol metadata',
            item_show_func=item_show_count(len(metadata)),
            length=len(metadata),
            show_percent=False,
        ) as symbols_map:
            for asset_id, symbol in symbols_map:
                # Attempt to load data from disk, the cache should have an
                # entry for each symbol at this point of the execution. If one
                # does not exist, we should fail.
                key = '{sym}.daily.frame'.format(sym=symbol)
                try:
                    raw_data = cache[key]
                except KeyError:
                    raise ValueError(
                      'Unable to find cached data for symbol:'
                      ' {0}'.format(symbol))

                # Perform and require post-processing of metadata.
                final_symbol_metadata = self.post_process_symbol_metadata(
                    asset_id,
                    metadata.iloc[asset_id],
                    raw_data,
                )

                # Record symbol's final metadata.
                final_metadata.iloc[asset_id] = final_symbol_metadata

            # Register all assets with the bundle's default exchange.
            final_metadata['exchange'] = self.exchange

        return final_metadata

    def _fetch_symbol_iter(self,
                           api_key,
                           cache,
                           symbol_map,
                           calendar,
                           start_session,
                           end_session,
                           data_frequency,
                           retries):

        for asset_id, symbol in symbol_map.iteritems():
            # Record start time of iteration, compare at end of iteration to
            # adhere to the datas source's rate limit policy.
            start_time = pd.Timestamp.utcnow()

            # Fetch new data if cached data is absent or stale, otherwise
            # returns the cached data unaltered.  The `should_sleep` flag
            # indicates that an API call was attempted, and that we should be
            # ensure aren't exceeding our rate limit before proceeding to the
            # next symbol. If the raw_data is updated, it is cached before
            # being returned.
            raw_data, should_sleep = self._maybe_update_symbol_frame(
                start_time,
                api_key,
                cache,
                symbol,
                calendar,
                start_session,
                end_session,
                data_frequency,
                retries,
            )

            # TODO(cfromknecht) further data validation?

            # Pass asset_id and symbol data to writer.
            yield asset_id, raw_data

            # If an API call was made during this iteration and the time to
            # reach this point was less than the inter-request `wait_time`,
            # sleep until after enough time has elapsed to prevent getting rate
            # limited.
            if should_sleep:
                remaining = pd.Timestamp.utcnow() - start_time + self.wait_time
                if remaining.value > 0:
                    sleep(remaining.value / 10**9)

    def _maybe_update_symbol_frame(self,
                                   start_time,
                                   api_key,
                                   cache,
                                   symbol,
                                   calendar,
                                   start_session,
                                   end_session,
                                   data_frequency,
                                   retries):

        # Attempt to load pre-existing symbol data from cache.
        key = '{sym}.{freq}.frame'.format(sym=symbol, freq=data_frequency)
        try:
            raw_data = cache[key]
        except KeyError:
            raw_data = None

        # Select the most recent date in cached dataset if it exists,
        # otherwise use the provided `start_session`.
        last = start_session
        if raw_data is not None and len(raw_data) > 0:
            last = raw_data.index[-1].tz_localize('UTC')

        should_sleep = False

        # Determine time at which cached data will be considered stale.
        cache_expiration = last + pd.Timedelta(days=2)
        if start_time <= cache_expiration and raw_data is not None:
            # Data is fresh enough to reuse, no need to update. Iterator can
            # proceed to next symbol directly since no API call was required.
            return raw_data, should_sleep

        # If we arrive here, we must have attempted an API call.
        # Setting this flag tells the iterator to pause before starting
        # the next asset, that we don't exceed the data source's rate
        # limit.
        should_sleep = True

        raw_data = self._fetch_symbol_frame(
            api_key,
            symbol,
            calendar,
            start_session,
            end_session,
            data_frequency,
            retries=retries,
        )

        # Cache latest symbol data.
        cache[key] = raw_data

        return raw_data, should_sleep

    def _fetch_symbol_frame(self,
                            api_key,
                            symbol,
                            calendar,
                            start_session,
                            end_session,
                            data_frequency,
                            retries=DEFAULT_RETRIES):

        # Data for symbol is old enough to attempt an update or is not
        # present in the cache.  Fetch raw data for a single symbol
        # with requested intervals and frequency. Retry as necessary.
        for _ in range(retries):
            try:
                raw_data = self.fetch_raw_symbol_frame(
                    api_key,
                    symbol,
                    calendar,
                    start_session,
                    end_session,
                    data_frequency,
                )
                raw_data.index = pd.to_datetime(raw_data.index, utc=True)

                # Filter incoming data to fit start and end sessions.
                raw_data = raw_data[
                    (raw_data.index >= start_session) &
                    (raw_data.index <= end_session)
                ]

                # Filter out any duplicates entries, keep last one, since
                # previous frame is probably an incomplete.
                raw_data = raw_data[~raw_data.index.duplicated(keep='last')]

                return raw_data

            except Exception:
                log.exception(
                    'Exception raised fetching {name} data. Retrying.'
                    .format(name=self.name)
                )
        else:
            raise ValueError(
                'Failed to download data for symbol {sym} '
                'after {n} attempts.'.format(
                    sym=symbol,
                    n=retries,
                )
            )


def _dtypes_to_cols(dtypes):
    return [name for name, _ in dtypes]
