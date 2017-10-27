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

import abc
from time import sleep

import numpy as np
import pandas as pd
from catalyst.assets._assets import TradingPair
from logbook import Logger

from catalyst.constants import LOG_LEVEL
from catalyst.data.data_portal import DataPortal
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.exchange_errors import (
    ExchangeRequestError,
    ExchangeBarDataError,
    PricingDataNotLoadedError)
from catalyst.exchange.exchange_utils import get_frequency, resample_history_df

log = Logger('DataPortalExchange', level=LOG_LEVEL)


class DataPortalExchangeBase(DataPortal):
    def __init__(self, *args, **kwargs):

        self.exchanges = kwargs.pop('exchanges', None)
        # TODO: put somewhere accessible by each algo
        self.retry_get_history_window = 5
        self.retry_get_spot_value = 5
        self.retry_delay = 5

        super(DataPortalExchangeBase, self).__init__(*args, **kwargs)

    def _get_history_window(self,
                            assets,
                            end_dt,
                            bar_count,
                            frequency,
                            field,
                            data_frequency,
                            ffill=True,
                            attempt_index=0):
        try:
            exchange_assets = dict()
            for asset in assets:
                if asset.exchange not in exchange_assets:
                    exchange_assets[asset.exchange] = list()

                exchange_assets[asset.exchange].append(asset)

            if len(exchange_assets) > 1:
                df_list = []
                for exchange_name in exchange_assets:
                    exchange = self.exchanges[exchange_name]
                    assets = exchange_assets[exchange_name]

                    df_exchange = self.get_exchange_history_window(
                        exchange,
                        assets,
                        end_dt,
                        bar_count,
                        frequency,
                        field,
                        data_frequency,
                        ffill)

                    df_list.append(df_exchange)

                # Merging the values values of each exchange
                return pd.concat(df_list)

            else:
                exchange = self.exchanges[list(exchange_assets.keys())[0]]
                return self.get_exchange_history_window(
                    exchange,
                    assets,
                    end_dt,
                    bar_count,
                    frequency,
                    field,
                    data_frequency,
                    ffill)

        except ExchangeRequestError as e:
            log.warn(
                'get history attempt {}: {}'.format(attempt_index, e)
            )
            if attempt_index < self.retry_get_history_window:
                sleep(self.retry_delay)
                return self._get_history_window(assets,
                                                end_dt,
                                                bar_count,
                                                frequency,
                                                field,
                                                data_frequency,
                                                ffill,
                                                attempt_index + 1)
            else:
                raise ExchangeBarDataError(
                    data_type='history',
                    attempts=attempt_index,
                    error=e
                )

    def get_history_window(self,
                           assets,
                           end_dt,
                           bar_count,
                           frequency,
                           field,
                           data_frequency=None,
                           ffill=True):

        if field == 'price':
            field = 'close'

        return self._get_history_window(assets,
                                        end_dt,
                                        bar_count,
                                        frequency,
                                        field,
                                        data_frequency,
                                        ffill)

    @abc.abstractmethod
    def get_exchange_history_window(self,
                                    exchange,
                                    assets,
                                    end_dt,
                                    bar_count,
                                    frequency,
                                    field,
                                    data_frequency,
                                    ffill=True):
        pass

    def _get_spot_value(self, assets, field, dt, data_frequency,
                        attempt_index=0):
        try:
            if isinstance(assets, TradingPair):
                exchange = self.exchanges[assets.exchange]
                spot_values = self.get_exchange_spot_value(
                    exchange, [assets], field, dt, data_frequency)

                if not spot_values:
                    return np.nan

                return spot_values[0]

            else:
                exchange_assets = dict()
                for asset in assets:
                    if asset.exchange not in exchange_assets:
                        exchange_assets[asset.exchange] = list()

                    exchange_assets[asset.exchange].append(asset)

                if len(list(exchange_assets.keys())) == 1:
                    exchange = self.exchanges[list(exchange_assets.keys())[0]]
                    return self.get_exchange_spot_value(
                        exchange, assets, field, dt, data_frequency)

                else:
                    spot_values = []
                    for exchange_name in exchange_assets:
                        exchange = self.exchanges[exchange_name]
                        assets = exchange_assets[exchange_name]
                        exchange_spot_values = self.get_exchange_spot_value(
                            exchange,
                            assets,
                            field,
                            dt,
                            data_frequency
                        )
                        if len(assets) == 1:
                            spot_values.append(exchange_spot_values)
                        else:
                            spot_values += exchange_spot_values

                    return spot_values

        except ExchangeRequestError as e:
            log.warn(
                'get spot value attempt {}: {}'.format(attempt_index, e)
            )
            if attempt_index < self.retry_get_spot_value:
                sleep(self.retry_delay)
                return self._get_spot_value(assets, field, dt, data_frequency,
                                            attempt_index + 1)
            else:
                raise ExchangeBarDataError(
                    data_type='spot',
                    attempts=attempt_index,
                    error=e
                )

    def get_spot_value(self, assets, field, dt, data_frequency):
        if field == 'price':
            field = 'close'

        return self._get_spot_value(assets, field, dt, data_frequency)

    @abc.abstractmethod
    def get_exchange_spot_value(self, exchange, assets, field, dt,
                                data_frequency):
        return

    def get_adjusted_value(self, asset, field, dt,
                           perspective_dt,
                           data_frequency,
                           spot_value=None):
        # TODO: does this pertain to cryptocurrencies?
        log.warn('get_adjusted_value is not implemented yet!')
        return spot_value


class DataPortalExchangeLive(DataPortalExchangeBase):
    def __init__(self, *args, **kwargs):
        super(DataPortalExchangeLive, self).__init__(*args, **kwargs)

    def get_exchange_history_window(self,
                                    exchange,
                                    assets,
                                    end_dt,
                                    bar_count,
                                    frequency,
                                    field,
                                    data_frequency,
                                    ffill=True):
        df = exchange.get_history_window(
            assets,
            end_dt,
            bar_count,
            frequency,
            field,
            data_frequency,
            ffill)
        return df

    def get_exchange_spot_value(self, exchange, assets, field, dt,
                                data_frequency):
        exchange_spot_values = exchange.get_spot_value(
            assets, field, dt, data_frequency)

        return exchange_spot_values


class DataPortalExchangeBacktest(DataPortalExchangeBase):
    def __init__(self, *args, **kwargs):
        super(DataPortalExchangeBacktest, self).__init__(*args, **kwargs)

        self.exchange_bundles = dict()

        self.history_loaders = dict()
        self.minute_history_loaders = dict()

        for exchange_name in self.exchanges:
            exchange = self.exchanges[exchange_name]
            self.exchange_bundles[exchange_name] = ExchangeBundle(exchange)

    def _get_first_trading_day(self, assets):
        first_date = None
        for asset in assets:
            if first_date is None or asset.start_date > first_date:
                first_date = asset.start_date
        return first_date

    def get_exchange_history_window(self,
                                    exchange,
                                    assets,
                                    end_dt,
                                    bar_count,
                                    frequency,
                                    field,
                                    data_frequency,
                                    ffill=True):
        """
        Fetching price history window from the exchange bundle.

        Using a try... except approach to minimize reads most of the time,
        when the data exists.

        :param exchange:
        :param assets:
        :param end_dt:
        :param bar_count:
        :param frequency:
        :param field:
        :param data_frequency:
        :param ffill:
        :return:
        """
        bundle = self.exchange_bundles[exchange.name]

        candle_size, unit, data_frequency = get_frequency(
            frequency, data_frequency
        )
        adj_bar_count = candle_size * bar_count

        series = bundle.get_history_window_series_and_load(
            assets=assets,
            end_dt=end_dt,
            bar_count=adj_bar_count,
            field=field,
            data_frequency=data_frequency
        )

        df = resample_history_df(pd.DataFrame(series), candle_size, field)
        return df

    def get_exchange_spot_value(self, exchange, assets, field, dt,
                                data_frequency):
        bundle = self.exchange_bundles[exchange.name]

        if data_frequency == 'daily':
            dt = dt.floor('1D')
        else:
            dt = dt.floor('1 min')

        try:
            return bundle.get_spot_values(assets, field, dt, data_frequency)

        except PricingDataNotLoadedError:
            log.info(
                'pricing data for {symbol} not found on {dt}'
                ', updating the bundles.'.format(
                    symbol=[asset.symbol for asset in assets],
                    dt=dt
                )
            )
            bundle.ingest_assets(
                assets=assets,
                start_dt=self._first_trading_day,
                end_dt=self._last_available_session,
                data_frequency=data_frequency,
                show_progress=True
            )
            return bundle.get_spot_values(
                assets, field, dt, data_frequency, True
            )
