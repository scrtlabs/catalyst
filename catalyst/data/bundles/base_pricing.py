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

from catalyst.data.bundles.base import BaseBundle
from catalyst.utils.memoize import lazyval


class BasePricingBundle(BaseBundle):
    @lazyval
    def md_dtypes(self):
        return [
            ('symbol', 'object'),
            ('start_date', 'datetime64[ns]'),
            ('end_date', 'datetime64[ns]'),
            ('ac_date', 'datetime64[ns]'),
            ('min_trade_size', 'float'),
        ]

    @lazyval
    def dtypes(self):
        return [
            ('date', 'datetime64[ns]'),
            ('open', 'float64'),
            ('high', 'float64'),
            ('low', 'float64'),
            ('close', 'float64'),
            ('volume', 'float64'),
        ]


class BaseCryptoPricingBundle(BasePricingBundle):
    @lazyval
    def calendar_name(self):
        return 'OPEN'

    @lazyval
    def minutes_per_day(self):
        return 1440

    @property
    def splits(self):
        return []

    @property
    def dividends(self):
        return []


class BaseEquityPricingBundle(BasePricingBundle):
    @lazyval
    def calendar_name(self):
        return 'NYSE'

    @lazyval
    def minutes_per_day(self):
        return 390

    @property
    def splits(self):
        return self._splits

    @property
    def dividends(self):
        return self._dividends
