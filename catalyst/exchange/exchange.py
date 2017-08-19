import abc
import json
from abc import ABCMeta, abstractmethod, abstractproperty
import collections

import pandas as pd
from catalyst.assets._assets import Asset
from catalyst.finance.order import ORDER_STATUS
from catalyst.finance.transaction import Transaction
from catalyst.data.data_portal import BASE_FIELDS

from catalyst.errors import (
    MultipleSymbolsFound,
    SymbolNotFound,
)
from datetime import timedelta
from logbook import Logger

log = Logger('Exchange')


class Exchange:
    __metaclass__ = ABCMeta

    def __init__(self):
        self.name = None
        self.trading_pairs = None
        self.assets = {}
        self._portfolio = None

    def get_trading_pairs(self, pairs):
        return [pair for pair in pairs if pair in self.trading_pairs]

    def get_symbol(self, asset):
        symbol = None

        for key in self.assets:
            if not symbol and self.assets[key].symbol == asset.symbol:
                symbol = key

        if not symbol:
            raise ValueError('Currency %s not supported by exchange %s' %
                             (asset['symbol'], self.name))

        return symbol

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

    def get_symbols(self, assets):
        symbols = []
        for asset in assets:
            symbols.append(self.get_symbol(asset))
        return symbols

    @staticmethod
    def asset_parser(asset):
        for key in asset:
            if key == 'start_date':
                asset[key] = pd.to_datetime(asset[key], utc=True)
        return asset

    def load_assets(self, assets_json):
        assets = json.loads(
            assets_json,
            object_hook=Exchange.asset_parser
        )

        for exchange_symbol in assets:
            asset_obj = Asset(
                sid=abs(hash(assets[exchange_symbol]['symbol'])) % (10 ** 4),
                exchange=self.name,
                end_date=pd.Timestamp.utcnow() + timedelta(minutes=300000),
                **assets[exchange_symbol]
            )
            self.assets[exchange_symbol] = asset_obj

    def check_open_orders(self):
        transactions = list()
        if self.portfolio.open_orders:
            for order_id in list(self.portfolio.open_orders):
                log.debug('found open order: {}'.format(order_id))
                order = self.get_order(order_id)
                log.debug('got updated order {}'.format(order))

                if order.status == ORDER_STATUS.FILLED:
                    transaction = Transaction(
                        asset=order.asset,
                        amount=order.amount,
                        dt=pd.Timestamp.utcnow(),
                        price=order.executed_price,
                        order_id=order.id,
                        commission=order.commission
                    )
                    transactions.append(transaction)

                    # TODO: use the transaction to pass the executed price
                    self.portfolio.execute_order(order)
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

    @abstractmethod
    def subscribe_to_market_data(self, symbol):
        pass

    @abstractproperty
    def positions(self):
        pass

    @abstractproperty
    def update_portfolio(self):
        pass

    @abstractproperty
    def portfolio(self):
        pass

    @abstractproperty
    def account(self):
        pass

    @abstractproperty
    def time_skew(self):
        pass

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
    def get_spot_value(self, assets, field, dt, data_frequency):
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
        """
        pass

    @abstractmethod
    def get_candles(self, data_frequency, assets,
                    end_dt=None, bar_count=None, limit=None):
        """
        Retrieve OHLC candles
        """
        pass

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
        log.debug(
            'fetching spot value {field} for symbol {symbol}'.format(
                symbol=asset.symbol,
                field=field
            )
        )

        ohlc = self.get_candles(data_frequency, asset)
        if field not in ohlc:
            raise KeyError('Invalid column: %s' % field)

        return ohlc[field]

    def get_history_window(self,
                           assets,
                           end_dt,
                           bar_count,
                           frequency,
                           fields,
                           data_frequency,
                           ffill=True):

        """

        :param assets:
        :param end_dt:
        :param bar_count:
        :param frequency:
        :param fields:
        :param data_frequency:
        :param ffill:

        :return df:
        If a single security and a single field were passed into data.history,
        a pandas Series is returned, indexed by date.

        If multiple securities and single field are passed in, the returned
        pandas DataFrame is indexed by date, and has assets as columns.

        If a single security and multiple fields are passed in, the returned
        pandas DataFrame is indexed by date, and has fields as columns.

        If multiple assets and multiple fields are passed in, the returned
        pandas Panel is indexed by field, has date as the major axis, and
        securities as the minor axis.
        """

        candles = self.get_candles(
            data_frequency=frequency,
            assets=assets,
            bar_count=bar_count,
            end_dt=end_dt
        )

        def get_single_field_series(candles):
            return pd.Series(
                map(lambda candle: candle[fields], candles),
                index=map(lambda candle: candle['last_traded'], candles)
            )

        df = None
        if len(assets) == 1:
            if type(fields) is str:
                asset = assets[0]
                df = get_single_field_series(candles[asset])
            else:
                raise NotImplementedError()
        else:
            if type(fields) is str:
                series = []
                for asset in assets:
                    item = get_single_field_series(candles[asset])
                    series.append(item)
                df = pd.concat(series, axis=1)
            else:
                raise NotImplementedError()

        return df

    @abc.abstractmethod
    def tickers(self, date, pairs):
        return
