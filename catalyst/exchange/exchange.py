import abc
import random
from time import sleep
import collections
from abc import ABCMeta, abstractmethod, abstractproperty
from datetime import timedelta

import numpy as np
import pandas as pd
from catalyst.assets._assets import Asset
from logbook import Logger

from catalyst.data.data_portal import BASE_FIELDS
from catalyst.errors import (
    SymbolNotFound,
)
from catalyst.finance.order import ORDER_STATUS
from catalyst.finance.transaction import Transaction
from catalyst.exchange.exchange_utils import get_exchange_symbols
from catalyst.exchange.exchange_portfolio import ExchangePortfolio

log = Logger('Exchange')


class Exchange:
    __metaclass__ = ABCMeta

    def __init__(self):
        self.name = None
        self.trading_pairs = None
        self.assets = {}
        self._portfolio = None
        self.minute_writer = None
        self.minute_reader = None

    @abstractproperty
    def positions(self):
        pass

    @abstractproperty
    def update_portfolio(self):
        pass

    @property
    def portfolio(self):
        """
        Return the Portfolio

        :return:
        """
        if self._portfolio is None:
            self._portfolio = ExchangePortfolio(
                start_date=pd.Timestamp.utcnow()
            )
            self.update_portfolio()

        return self._portfolio

    @abstractproperty
    def account(self):
        pass

    @abstractproperty
    def time_skew(self):
        pass

    def get_symbol(self, asset):
        """
        Get the exchange specific symbol of the given asset.

        :param asset: Asset
        :return: symbol: str
        """
        symbol = None

        for key in self.assets:
            if not symbol and self.assets[key].symbol == asset.symbol:
                symbol = key

        if not symbol:
            raise ValueError('Currency %s not supported by exchange %s' %
                             (asset['symbol'], self.name))

        return symbol

    def get_symbols(self, assets):
        """
        Get a list of symbols corresponding to each given asset.

        :param assets: Asset[]
        :return:
        """
        symbols = []

        for asset in assets:
            symbols.append(self.get_symbol(asset))

        return symbols

    def get_asset(self, symbol):
        """
        Find an Asset on the current exchange based on its Catalyst symbol
        :param symbol: the [target]_[base] currency pair symbol
        :return: Asset
        """
        asset = None

        for key in self.assets:
            if not asset and self.assets[key].symbol.lower() == symbol.lower():
                asset = self.assets[key]

        if not asset:
            raise SymbolNotFound('Asset not found: %s' % symbol)

        return asset

    def fetch_symbol_map(self):
        return get_exchange_symbols(self.name)

    def load_assets(self):
        """
        Populate the 'assets' attribute with a dictionary of Assets.
        The key of the resulting dictionary is the exchange specific
        currency pair symbol. The universal symbol is contained in the
        'symbol' attribute of each asset.


        Notes
        -----
        The sid of each asset is calculated based on a numeric hash of the
        universal symbol. This simple approach avoids maintaining a mapping
        of sids.

        This method can be overridden if an exchange offers equivalent data
        via its api.
        """

        symbol_map = self.fetch_symbol_map()
        for exchange_symbol in symbol_map:
            asset = symbol_map[exchange_symbol]
            symbol = asset['symbol']
            asset_name = ' / '.join(symbol.split('_')).upper()

            asset_obj = Asset(
                symbol=symbol,
                asset_name=asset_name,
                sid=abs(hash(symbol)) % (10 ** 4),
                exchange=self.name,
                start_date=pd.to_datetime(asset['start_date'], utc=True),
                end_date=pd.Timestamp.utcnow() + timedelta(minutes=300000),
            )

            self.assets[exchange_symbol] = asset_obj

    def check_open_orders(self):
        """
        Loop through the list of open orders in the Portfolio object.
        For each executed order found, create a transaction and apply to the
        Portfolio.

        :return:
        transactions: Transaction[]
        """
        transactions = list()
        if self.portfolio.open_orders:
            for order_id in list(self.portfolio.open_orders):
                log.debug('found open order: {}'.format(order_id))

                order, executed_price = self.get_order(order_id)
                log.debug('got updated order {} {}'.format(
                    order, executed_price))

                if order.status == ORDER_STATUS.FILLED:
                    transaction = Transaction(
                        asset=order.asset,
                        amount=order.amount,
                        dt=pd.Timestamp.utcnow(),
                        price=executed_price,
                        order_id=order.id,
                        commission=order.commission
                    )
                    transactions.append(transaction)

                    self.portfolio.execute_order(order, transaction)

                elif order.status == ORDER_STATUS.CANCELLED:
                    self.portfolio.remove_order(order)

                else:
                    delta = pd.Timestamp.utcnow() - order.dt
                    log.info(
                        'order {order_id} still open after {delta}'.format(
                            order_id=order_id,
                            delta=delta
                        )
                    )
        return transactions

    def get_spot_value(self, assets, field, dt=None, data_frequency='minute'):
        """
        Public API method that returns a scalar value representing the value
        of the desired asset's field at either the given dt.

        Parameters
        ----------
        assets : Asset, ContinuousFuture, or iterable of same.
            The asset or assets whose data is desired.
        field : {'open', 'high', 'low', 'close', 'volume',
                 'price', 'last_traded'}
            The desired field of the asset.
        dt : pd.Timestamp
            The timestamp for the desired value.
        data_frequency : str
            The frequency of the data to query; i.e. whether the data is
            'daily' or 'minute' bars

        Returns
        -------
        value : float, int, or pd.Timestamp
            The spot value of ``field`` for ``asset`` The return type is based
            on the ``field`` requested. If the field is one of 'open', 'high',
            'low', 'close', or 'price', the value will be a float. If the
            ``field`` is 'volume' the value will be a int. If the ``field`` is
            'last_traded' the value will be a Timestamp.

        Bitfinex timeframes
        -------------------
        Available values: '1m', '5m', '15m', '30m', '1h', '3h', '6h', '12h',
         '1D', '7D', '14D', '1M'
        """
        if field not in BASE_FIELDS:
            raise KeyError('Invalid column: ' + str(field))

        if isinstance(assets, collections.Iterable):
            values = list()
            for asset in assets:
                value = self.get_single_spot_value(
                    asset, field, data_frequency)
                values.append(value)

            return values
        else:
            return self.get_single_spot_value(
                assets, field, data_frequency)

    def get_single_spot_value(self, asset, field, data_frequency):
        """
        Similar to 'get_spot_value' but for a single asset

        Note
        ----
        We're writing each minute bar to disk using zipline's machinery.
        This is especially useful when running multiple algorithms
        concurrently. By using local data when possible, we try to reaching
        request limits on exchanges.

        :param asset:
        :param field:
        :param data_frequency:
        :return value: The spot value of the given asset / field
        """
        log.debug(
            'fetching spot value {field} for symbol {symbol}'.format(
                symbol=asset.symbol,
                field=field
            )
        )

        if field == 'price':
            field = 'close'

        # Don't use a timezone here
        dt = pd.Timestamp.utcnow().floor('1 min')
        value = None
        if self.minute_reader is not None:
            try:
                # Slight delay to minimize the chances that multiple algos
                # might try to hit the cache at the exact same time.
                sleep_time = random.uniform(0.5, 0.8)
                sleep(sleep_time)
                # TODO: This does not always! Why is that? Open an issue with zipline.
                # See: https://github.com/zipline-live/zipline/issues/26
                value = self.minute_reader.get_value(
                    sid=asset.sid,
                    dt=dt,
                    field=field
                )
            except Exception as e:
                log.warn('minute data not found: {}'.format(e))

        if value is None or np.isnan(value):
            ohlc = self.get_candles(data_frequency, asset)
            if field not in ohlc:
                raise KeyError('Invalid column: %s' % field)

            if self.minute_writer is not None:
                df = pd.DataFrame(
                    [ohlc],
                    index=pd.DatetimeIndex([dt]),
                    columns=['open', 'high', 'low', 'close', 'volume']
                )

                try:
                    self.minute_writer.write_sid(
                        sid=asset.sid,
                        df=df
                    )
                    log.debug('wrote minute data: {}'.format(dt))
                except Exception as e:
                    log.warn(
                        'unable to write minute data: {} {}'.format(dt, e))

            value = ohlc[field]
            log.debug('got spot value: {}'.format(value))
        else:
            log.debug('got spot value from cache: {}'.format(value))

        return value

    def get_history_window(self,
                           assets,
                           end_dt,
                           bar_count,
                           frequency,
                           field,
                           data_frequency,
                           ffill=True):

        """
        Public API method that returns a dataframe containing the requested
        history window.  Data is fully adjusted.

        Parameters
        ----------
        assets : list of catalyst.data.Asset objects
            The assets whose data is desired.

        end_dt: not applicable to cryptocurrencies

        bar_count: int
            The number of bars desired.

        frequency: string
            "1d" or "1m"

        field: string
            The desired field of the asset.

        data_frequency: string
            The frequency of the data to query; i.e. whether the data is
            'daily' or 'minute' bars.

        # TODO: fill how?
        ffill: boolean
            Forward-fill missing values. Only has effect if field
            is 'price'.

        Returns
        -------
        A dataframe containing the requested data.
        """

        candles = self.get_candles(
            data_frequency=frequency,
            assets=assets,
            bar_count=bar_count,
        )

        frames = []
        for asset in assets:
            asset_candles = candles[asset]

            asset_data = dict()
            asset_data[asset] = map(lambda candle: candle[field],
                                    asset_candles)

            dates = map(lambda candle: candle['last_traded'],
                        asset_candles)

            df = pd.DataFrame(asset_data, index=dates)
            frames.append(df)

        return pd.concat(frames)

    @abstractmethod
    def order(self, asset, amount, limit_price, stop_price, style):
        """Place an order.

        Parameters
        ----------
        asset : Asset
            The asset that this order is for.
        amount : int
            The amount of shares to order. If ``amount`` is positive, this is
            the number of shares to buy or cover. If ``amount`` is negative,
            this is the number of shares to sell or short.
        limit_price : float, optional
            The limit price for the order.
        stop_price : float, optional
            The stop price for the order.
        style : ExecutionStyle, optional
            The execution style for the order.

        Returns
        -------
        order_id : str or None
            The unique identifier for this order, or None if no order was
            placed.

        Notes
        -----
        The ``limit_price`` and ``stop_price`` arguments provide shorthands for
        passing common execution styles. Passing ``limit_price=N`` is
        equivalent to ``style=LimitOrder(N)``. Similarly, passing
        ``stop_price=M`` is equivalent to ``style=StopOrder(M)``, and passing
        ``limit_price=N`` and ``stop_price=M`` is equivalent to
        ``style=StopLimitOrder(N, M)``. It is an error to pass both a ``style``
        and ``limit_price`` or ``stop_price``.

        See Also
        --------
        :class:`catalyst.finance.execution.ExecutionStyle`
        :func:`catalyst.api.order_value`
        :func:`catalyst.api.order_percent`
        """
        pass

    @abstractmethod
    def get_open_orders(self, asset):
        """Retrieve all of the current open orders.

        Parameters
        ----------
        asset : Asset
            If passed and not None, return only the open orders for the given
            asset instead of all open orders.

        Returns
        -------
        open_orders : dict[list[Order]] or list[Order]
            If no asset is passed this will return a dict mapping Assets
            to a list containing all the open orders for the asset.
            If an asset is passed then this will return a list of the open
            orders for this asset.
        """
        pass

    @abstractmethod
    def get_order(self, order_id):
        """Lookup an order based on the order id returned from one of the
        order functions.

        Parameters
        ----------
        order_id : str
            The unique identifier for the order.

        Returns
        -------
        order : Order
            The order object.
        execution_price: float
            The execution price per share of the order
        """
        pass

    @abstractmethod
    def cancel_order(self, order_param):
        """Cancel an open order.

        Parameters
        ----------
        order_param : str or Order
            The order_id or order object to cancel.
        """
        pass

    @abstractmethod
    def get_candles(self, data_frequency, assets, bar_count=None):
        """
        Retrieve OHLCV candles for the given assets

        :param data_frequency:
        :param assets:
        :param end_dt:
        :param bar_count:
        :param limit:
        :return:
        """
        pass

    @abc.abstractmethod
    def tickers(self, assets):
        """
        Retrieve current tick data for the given assets

        :param assets:
        :return:
        """
        pass

    @abc.abstractmethod
    def get_account(self):
        """
        Retrieve the account parameters.
        :return:
        """
        pass
