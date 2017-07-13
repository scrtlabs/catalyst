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
from time import time, sleep

from abc import abstractmethod
import logbook
import pandas as pd

from . import core as bundles

from catalyst.utils.cli import (
    item_show_count,
    maybe_show_progress
)
from catalyst.utils.memoize import lazyval

logbook.StderrHandler().push_application()
log = logbook.Logger(__name__)

class BaseBundle(object):
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
               output_dir):

        api_key = environ.get('CATALYST_API_KEY')
        retries = environ.get('CATALYST_DOWNLOAD_ATTEMPTS', 5)
        use_local = environ.get('CATALYST_INGEST_LOCAL', 0) > 0

        if use_local:
            raw_metadata = self._fetch_metadata_frame(
                api_key,
                cache=cache,
                retries=retries,
                environ=environ,
                show_progress=show_progress,
            )

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

            metadata = self._post_process_metadata(
                raw_metadata,
                cache,
                show_progress=show_progress,
            )
            asset_db_writer.write(metadata)

            if '5-minute' in self.frequencies:
                minute_bar_writer.write(
                    self._fetch_symbol_iter(
                        api_key,
                        cache,
                        symbol_map,
                        calendar,
                        start_session,
                        end_session,
                        '5-minute',
                        retries,
                    ),
                    show_progress=show_progress,
                )

            adjustment_writer.write()
        else:
            self._download(show_progress, output_dir)

    def _download(self, show_progress, output_dir):
        if show_progress:
            data = bundles.download_with_progress(
                self.tar_url,
                chunk_size=bundles.ONE_MEGABYTE,
                label='Downloading bundle: {name}'.format(name=self.name),
            )
        else:
            data = bundles.download_without_progress(self.tar_url)

        with tarfile.open('r', fileobj=data) as tar:
            if show_progress:
                print 'Writing data to {dir}'.format(dir=output_dir)
            tar.extractall(output_dir)
        

    def _fetch_metadata_frame(self,
                             api_key,
                             cache,
                             retries=5,
                             environ=None,
                             show_progress=False):
        
        raw_iter = self._fetch_metadata_iter(api_key, cache, retries, environ)

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

    def _post_process_metadata(self, metadata, cache, show_progress=False):
        final_metadata = pd.DataFrame(
            columns=self.md_column_names,
            index=metadata.index,
        )
        
        with maybe_show_progress(
            metadata.symbol.iteritems(),
            show_progress,
            label='Post-processing symbol metadata',
            item_show_func=item_show_count(len(metadata)),
            length=len(metadata),
            show_percent=False,
        ) as symbols_map:
            for asset_id, symbol in symbols_map:
                try:
                    raw_data = cache[symbol]
                except KeyError:
                    raise ValueError(
                      'Unable to find cached data for symbol: {0}'.format(symbol)
                    )

                final_symbol_metadata = self.post_process_symbol_metadata(
                    metadata.iloc[asset_id],
                    raw_data,        
                )

                final_metadata.iloc[asset_id] = final_symbol_metadata

            final_metadata['exchange'] = self.exchange

        return final_metadata
        
    def _fetch_metadata_iter(self, api_key, cache, retries, environ):
        for page_number in count(1):
            key = 'metadata-page-{pn}'.format(pn=page_number)
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
                else:
                    raise ValueError(
                        'Failed to download metadata page %d after %d '
                        'attempts.'.format(page_number, retries),
                    )


            if raw.empty:
                # empty DataFrame signals completion
                break

            # update cached value for key
            cache[key] = raw

            yield raw

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
            # next symbol. If the raw_data is updated, it is cached before being
            # returned.
            raw_data, should_sleep = self._maybe_update_symbol_frame(
                start_time,
                api_key,
                cache,
                symbol,
                start_session,
                end_session,
                data_frequency,
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
                                   start_session,
                                   end_session,
                                   data_frequency):
        try:
            raw_data = cache[symbol]
        except KeyError:
            raw_data = None

        # Select the most recent date in cached dataset if it exists,
        # otherwise use the provided `start_session`.
        last = (
            raw_data.index[-1].tz_localize('UTC')
            if raw_data is not None and not raw_data.empty else
            start_session
        )

        # Determine time at which cached data will be considered stale.
        cache_expiration = last + pd.Timedelta(minutes=5)
        if start_time <= cache_expiration:
            # Data is fresh enough to reuse, no need to update. Iterator can
            # proceed to next symbol directly since no API call was required.
            should_sleep = False
        else:
            # Data for symbol is old enough to attempt an update or is not
            # present in the cache.  Fetch raw data for a single symbol 
            # with requested intervals and frequency.
            raw_diff = self.fetch_raw_symbol_frame(
                api_key,
                symbol,
                last,
                end_session,
                data_frequency,
            )

            # Filter incoming data to minimize overlap.
            raw_diff = raw_diff[
                (raw_diff.index >= last) &
                (raw_diff.index <= end_session)
            ]

            # Append incoming data to cached data if it exists,
            # otherwise treat incoming data as the entire raw dataset.
            raw_data = cache[symbol] = (
                raw_data.append(raw_diff)
                if raw_data is not None else
                raw_diff
            )

            # Filter out any duplicates entries, keep last one as previous
            # one was probably an incomplete frame.
            raw_data = raw_data[~raw_data.index.duplicated(keep='last')]

            # If we arrive here, we must have attempted an API call.
            # This flag tells the iterator to pause before starting the next
            # asset, that we don't exceed the data source's rate limit.
            should_sleep = True

        return raw_data, should_sleep

    def _write_symbol_for_freq(self,
                               pricing_iter,
                               data_frequency,
                               daily_bar_writer,
                               minute_bar_writer,
                               assets,
                               show_progress=False):
        if data_frequency == 'daily':
            daily_bar_writer.write(
                pricing_iter,
                assets=assets,
                show_progress=show_progress,
            )
        elif data_frequency == '5-minute':
            minute_bar_writer.write(
                pricing_iter,
                show_progress=show_progress,
            )
        elif data_frequency == 'minute':
            minute_bar_writer.write(
                pricing_iter,
                show_progress=show_progress,
            )
        else:
            raise ValueError(
                'Unsupported data-frequency: {0}'.format(data_frequency)
            )

def _dtypes_to_cols(dtypes):
    return [name for name, _ in dtypes]
