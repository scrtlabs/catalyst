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

from datetime import datetime

import pandas as pd
from six.moves.urllib.parse import urlencode

from catalyst.data.bundles.core import register_bundle
from catalyst.data.bundles.base_pricing import BaseEquityPricingBundle
from catalyst.utils.memoize import lazyval

"""
Module for building a complete daily dataset from Quandl's WIKI dataset.
"""
from logbook import Logger

from catalyst.constants import LOG_LEVEL
from catalyst.utils.calendars import register_calendar_alias


log = Logger(__name__, level=LOG_LEVEL)
seconds_per_call = (pd.Timedelta('10 minutes') / 2000).total_seconds()


class QuandlBundle(BaseEquityPricingBundle):
    @lazyval
    def name(self):
        return 'quandl'

    @lazyval
    def exchange(self):
        return 'QUANDL'

    @lazyval
    def frequencies(self):
        return set(('daily',))

    @lazyval
    def tar_url(self):
        return 'https://s3.amazonaws.com/quantopian-public-zipline-data/quandl'

    @lazyval
    def wait_time(self):
        return pd.Timedelta(milliseconds=300)

    @lazyval
    def _excluded_symbols(self):
        """
        Invalid symbols that quandl has had in its metadata:
        """
        return frozenset({'TEST123456789'})

    def fetch_raw_metadata_frame(self, api_key, page_number):
        raw = pd.read_csv(
            self._format_metadata_url(api_key, page_number),
            date_parser=pd.tseries.tools.to_datetime,
            parse_dates=[
                'oldest_available_date',
                'newest_available_date',
            ],
            dtype={
                'dataset_code': 'str',
                'name': 'str',
                'oldest_available_date': 'str',
                'newest_available_date': 'str',
            },
            usecols=[
                'dataset_code',
                'name',
                'oldest_available_date',
                'newest_available_date',
            ],
        ).rename(
            columns={
                'dataset_code': 'symbol',
                'name': 'asset_name',
                'oldest_available_date': 'start_date',
                'newest_available_date': 'end_date',
            },
        )

        raw['start_date'] = raw['start_date'].astype(datetime)
        raw['end_date'] = raw['end_date'].astype(datetime)
        raw['ac_date'] = raw['end_date'] + pd.Timedelta(days=1)

        # Filter out invalid symbols
        raw = raw[~raw.symbol.isin(self._excluded_symbols)]

        # cut out all the other stuff in the name column. We need to
        # escape the paren because it is actually splitting on a regex
        raw.asset_name = raw.asset_name.str.split(r' \(', 1).str.get(0)

        return raw

    def fetch_raw_symbol_frame(self,
                               api_key,
                               symbol,
                               calendar,
                               start_session,
                               end_session,
                               data_frequency):
        raw_data = pd.read_csv(
            self._format_wiki_url(
                api_key,
                symbol,
                start_session,
                end_session,
                data_frequency,
            ),
            parse_dates=['Date'],
            index_col='Date',
            usecols=[
                'Open',
                'High',
                'Low',
                'Close',
                'Volume',
                'Date',
                'Ex-Dividend',
                'Split Ratio',
            ],
            na_values=['NA'],
        ).rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Date': 'date',
            'Ex-Dividend': 'ex_dividend',
            'Split Ratio': 'split_ratio',
        })

        sessions = calendar.sessions_in_range(start_session, end_session)

        return raw_data.reindex(
            sessions.tz_localize(None),
            copy=False,
        ).fillna(0.0)

    def post_process_symbol_metadata(self, asset_id, sym_md, sym_data):
        self._update_splits(asset_id, sym_data)
        self._update_dividends(asset_id, sym_data)

        return sym_md

    def _update_splits(self, asset_id, raw_data):
        split_ratios = raw_data.split_ratio
        df = pd.DataFrame({'ratio': 1 / split_ratios[split_ratios != 1]})
        df.index.name = 'effective_date'
        df.reset_index(inplace=True)
        df['sid'] = asset_id
        self.splits.append(df)

    def _update_dividends(self, asset_id, raw_data):
        divs = raw_data.ex_dividend
        df = pd.DataFrame({'amount': divs[divs != 0]})
        df.index.name = 'ex_date'
        df.reset_index(inplace=True)
        df['sid'] = asset_id
        # we do not have this data in the WIKI dataset
        df['record_date'] = df['declared_date'] = df['pay_date'] = pd.NaT
        self.dividends.append(df)

    def _format_metadata_url(self, api_key, page_number):
        """Build the query RL for the quandl WIKI metadata.
        """
        query_params = [
            ('per_page', '100'),
            ('sort_by', 'id'),
            ('page', str(page_number)),
            ('database_code', 'WIKI'),
        ]
        if api_key is not None:
            query_params = [('api_key', api_key)] + query_params

        return (
            'https://www.quandl.com/api/v3/datasets.csv?'
            + urlencode(query_params)
        )

    def _format_wiki_url(self,
                         api_key,
                         symbol,
                         start_date,
                         end_date,
                         data_frequency):
        """
        Build a query URL for a quandl WIKI dataset.
        """
        query_params = [
            ('start_date', start_date.strftime('%Y-%m-%d')),
            ('end_date', end_date.strftime('%Y-%m-%d')),
            ('order', 'asc'),
        ]
        if api_key is not None:
            query_params = [('api_key', api_key)] + query_params

        return (
            "https://www.quandl.com/api/v3/datasets/WIKI/"
            "{symbol}.csv?{query}".format(
                symbol=symbol,
                query=urlencode(query_params),
            )
        )


register_calendar_alias('QUANDL', 'NYSE')
register_bundle(QuandlBundle)
