import abc
import datetime

import numpy as np
import pandas as pd
from catalyst.assets._assets import TradingPair
from catalyst.constants import LOG_LEVEL, AUTO_INGEST
from catalyst.data.data_portal import DataPortal
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.exchange_errors import (
    ExchangeRequestError,
    PricingDataNotLoadedError)
from catalyst.exchange.utils.exchange_utils import resample_history_df, \
    group_assets_by_exchange
from catalyst.exchange.utils.datetime_utils import get_frequency, get_start_dt
from logbook import Logger
from redo import retry

log = Logger('DataPortalExchange', level=LOG_LEVEL)


class DataPortalExchangeBase(DataPortal):
    def __init__(self, *args, **kwargs):
        self.attempts = dict(
            get_spot_value_attempts=5,
            get_history_window_attempts=5,
            retry_sleeptime=5,
        )

        super(DataPortalExchangeBase, self).__init__(*args, **kwargs)

    def _get_history_window(self,
                            assets,
                            end_dt,
                            bar_count,
                            frequency,
                            field,
                            data_frequency,
                            ffill=True):
        exchange_assets = group_assets_by_exchange(assets)
        if len(exchange_assets) > 1:
            df_list = []
            for exchange_name in exchange_assets:
                assets = exchange_assets[exchange_name]

                df_exchange = self.get_exchange_history_window(
                    exchange_name,
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
            exchange_name = list(exchange_assets.keys())[0]
            return self.get_exchange_history_window(
                exchange_name,
                assets,
                end_dt,
                bar_count,
                frequency,
                field,
                data_frequency,
                ffill)

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

        return retry(
            action=self._get_history_window,
            attempts=self.attempts['get_history_window_attempts'],
            sleeptime=self.attempts['retry_sleeptime'],
            retry_exceptions=(ExchangeRequestError,),
            cleanup=lambda: log.warn('fetching history again.'),
            args=(assets,
                  end_dt,
                  bar_count,
                  frequency,
                  field,
                  data_frequency,
                  ffill))

    @abc.abstractmethod
    def get_exchange_history_window(self,
                                    exchange_name,
                                    assets,
                                    end_dt,
                                    bar_count,
                                    frequency,
                                    field,
                                    data_frequency,
                                    ffill=True):
        pass

    def _get_spot_value(self, assets, field, dt, data_frequency):
        if isinstance(assets, TradingPair):
            spot_values = self.get_exchange_spot_value(
                assets.exchange, [assets], field, dt, data_frequency)

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
                exchange_name = list(exchange_assets.keys())[0]
                return self.get_exchange_spot_value(
                    exchange_name, assets, field, dt, data_frequency)

            else:
                spot_values = []
                for exchange_name in exchange_assets:
                    assets = exchange_assets[exchange_name]
                    exchange_spot_values = self.get_exchange_spot_value(
                        exchange_name,
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

    def get_spot_value(self, assets, field, dt, data_frequency):
        if field == 'price':
            field = 'close'

        return retry(
            action=self._get_spot_value,
            attempts=self.attempts['get_spot_value_attempts'],
            sleeptime=self.attempts['retry_sleeptime'],
            retry_exceptions=(ExchangeRequestError,),
            cleanup=lambda: log.warn('fetching spot value again.'),
            args=(assets, field, dt, data_frequency))

    @abc.abstractmethod
    def get_exchange_spot_value(self, exchange_name, assets, field, dt,
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
        self.exchanges = kwargs.pop('exchanges', None)
        super(DataPortalExchangeLive, self).__init__(*args, **kwargs)

    def get_exchange_history_window(self,
                                    exchange_name,
                                    assets,
                                    end_dt,
                                    bar_count,
                                    frequency,
                                    field,
                                    data_frequency,
                                    ffill=True):
        """
        Fetching price history window from the exchange.

        Parameters
        ----------
        exchange_name: Exchange
        assets: list[TradingPair]
        end_dt: datetime
        bar_count: int
        frequency: str
        field: str
        data_frequency: str
        ffill: bool

        Returns
        -------
        DataFrame

        """
        exchange = self.exchanges[exchange_name]

        df = exchange.get_history_window(
            assets,
            end_dt,
            bar_count,
            frequency,
            field,
            data_frequency,
            False)
        return df

    def get_exchange_spot_value(self, exchange_name, assets, field, dt,
                                data_frequency):
        """
        A spot value for the exchange.

        Parameters
        ----------
        exchange_name: str
        assets: list[TradingPair]
        field: str
        dt: datetime
        data_frequency: str

        Returns
        -------
        float

        """
        exchange = self.exchanges[exchange_name]
        exchange_spot_values = exchange.get_spot_value(
            assets, field, dt, data_frequency)

        return exchange_spot_values


class DataPortalExchangeBacktest(DataPortalExchangeBase):
    def __init__(self, *args, **kwargs):
        self.exchange_names = kwargs.pop('exchange_names', None)

        super(DataPortalExchangeBacktest, self).__init__(*args, **kwargs)

        self.exchange_bundles = dict()
        self.history_loaders = dict()
        self.minute_history_loaders = dict()

        for name in self.exchange_names:
            self.exchange_bundles[name] = ExchangeBundle(name)

    def _get_first_trading_day(self, assets):
        first_date = None
        for asset in assets:
            if first_date is None or asset.start_date > first_date:
                first_date = asset.start_date
        return first_date

    def get_exchange_history_window(self,
                                    exchange_name,
                                    assets,
                                    end_dt,
                                    bar_count,
                                    frequency,
                                    field,
                                    data_frequency,
                                    ffill=True):
        """
        Fetching price history window from the exchange bundle.

        Parameters
        ----------
        exchange: Exchange
        assets: list[TradingPair]
        end_dt: datetime
        bar_count: int
        frequency: str
        field: str
        data_frequency: str
        ffill: bool

        Returns
        -------
        DataFrame

        """
        # TODO: verify that the exchange supports the timeframe
        bundle = self.exchange_bundles[exchange_name]  # type: ExchangeBundle

        freq, candle_size, unit, adj_data_frequency = get_frequency(
            frequency, data_frequency, supported_freqs=['T', 'D']
        )
        adj_bar_count = candle_size * bar_count

        if data_frequency == "minute":
            # for minute frequency always request data until the
            # current minute (do not include the current minute)
            last_dt_for_series = end_dt - datetime.timedelta(minutes=1)

            # read the minute bundles for daily frequency to
            # support last partial candle
            # TODO: optimize this by applying this logic only for the last day
            if adj_data_frequency == 'daily':
                adj_data_frequency = 'minute'
                adj_bar_count = adj_bar_count * 1440

        else:  # data_frequency == "daily":
            last_dt_for_series = end_dt

        series = bundle.get_history_window_series_and_load(
            assets=assets,
            end_dt=last_dt_for_series,
            bar_count=adj_bar_count,
            field=field,
            data_frequency=adj_data_frequency,
            algo_end_dt=self._last_available_session,
        )

        start_dt = get_start_dt(last_dt_for_series, adj_bar_count,
                                adj_data_frequency, False)
        df = resample_history_df(pd.DataFrame(series), freq, field, start_dt)

        return df

    def get_exchange_spot_value(self,
                                exchange_name,
                                assets,
                                field,
                                dt,
                                data_frequency
                                ):
        """
        A spot value for the exchange bundle. Try to ingest data if not in
        the bundle.

        Parameters
        ----------
        exchange_name: str
        assets: list[TradingPair]
        field: str
        dt: datetime
        data_frequency: str

        Returns
        -------
        float

        """
        bundle = self.exchange_bundles[exchange_name]
        if data_frequency == 'daily':
            dt = dt.floor('1D')
        else:
            dt = dt.floor('1 min')

        if AUTO_INGEST:
            try:
                return bundle.get_spot_values(
                    assets, field, dt, data_frequency
                )
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
        else:
            return bundle.get_spot_values(assets, field, dt, data_frequency)
