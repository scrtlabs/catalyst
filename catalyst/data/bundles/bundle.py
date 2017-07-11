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

from catalyst.utils.cli import maybe_show_progress
from catalyst.utils.memoize import lazyval

logbook.StderrHandler().push_application()
log = logbook.Logger(__name__)

class AbstractBundle(object):
    def __init__(self):
        pass
        
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

            """
            for data_frequency in self.frequencies:
                self._write_symbol_for_freq(
                    self._fetch_symbol_iter(
                        api_key,
                        cache,
                        symbol_map,
                        calendar,
                        start_session,
                        end_session,
                        data_frequency,
                        retries,
                    ),
                    data_frequency,
                    daily_bar_writer,
                    minute_bar_writer,
                    assets=raw_metadata.index,
                    show_progress=show_progress,
                )
            """
                
                    

            metadata = self._post_process_metadata(raw_metadata, cache)
            asset_db_writer.write(metadata)

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
        
        def item_show_func(_, _it=iter(count())):
            return 'Downloading metadata page: {0}'.format(next(_it))

        with maybe_show_progress(
            raw_iter,
            show_progress,
            item_show_func=item_show_func,
            label='Fetching {bundle} metadata:'.format(bundle=self.name),
        ) as blocks:
            metadata = pd.concat(blocks, ignore_index=True)
        
        return metadata

    def _post_process_metadata(self, metadata, cache):
        final_metadata = pd.DataFrame(
            columns=self.md_column_names,
            index=metadata.index,
        )

        for asset_id, symbol in metadata.symbol.iteritems():
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

                # update cached value for key
                cache[key] = raw

            if raw.empty:
                # empty DataFrame signals completion
                break

            yield raw

    def _fetch_symbol_iter(self,
                           api_key,
                           cache,
                           symbol_map,
                           calendar,
                           start_session,
                           end_session,
                           frequency,
                           retries):

        for asset_id, symbol in symbol_map.iteritems():
            start_time = pd.Timestamp.utcnow()
            try:
                raw_data = cache[symbol]
            except KeyError:
                raw_data = None
            
            if raw_data is not None and not raw_data.empty:
                last = raw_data.index[-1].tz_localize('UTC')
            else:
                last = start_session

            next_start_time = last + pd.Timedelta(minutes=5)
            if start_time > next_start_time:
                raw_diff = self.fetch_raw_symbol_frame(
                    api_key,
                    symbol,
                    last,
                    end_session,
                    frequency,
                )
                raw_diff = raw_diff[
                    (raw_diff.index >= last) &
                    (raw_diff.index <= end_session)
                ]

                raw_data = cache[symbol] = (
                    raw_data.append(raw_diff)
                    if raw_data is not None else
                    raw_diff
                )

                raw_data = raw_data[~raw_data.index.duplicated(keep='last')]

                should_sleep = True
            else:
                should_sleep = False      

            """
            sessions = calendar.sessions_in_range(start_session, end_session)

            print 'raw_data before:\n', raw_data.head()
            raw_data = raw_data.reindex(
                sessions,
                copy=False,
            ).fillna(0.0)
            print 'raw_data after:\n', raw_data.head()
            """

            yield asset_id, raw_data

            if should_sleep:
                remaining = pd.Timestamp.utcnow() - start_time + self.wait_time
                if remaining.value > 0:
                    sleep(remaining.value / 10**9)

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
                assets=assets,
                show_progress=show_progress,
            )
        elif data_frequency == 'minute':
            minute_bar_writer.write(
                pricing_iter,
                assets=assets,
                show_progress=show_progress,
            )
        else:
            raise ValueError(
                'Unsupported data-frequency: {0}'.format(data_frequency)
            )

def _dtypes_to_cols(dtypes):
    return [name for name, _ in dtypes]
