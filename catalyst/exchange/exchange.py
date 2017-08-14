import abc
from collections import namedtuple
from abc import ABCMeta, abstractmethod, abstractproperty
import json
import pandas as pd
from catalyst.assets._assets import Asset


class Exchange:
    __metaclass__ = ABCMeta

    def __init__(self):
        self.name = None
        self.trading_pairs = None
        self.assets = {}

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
            if not asset and self.assets[key].symbol == symbol:
                asset = self.assets[key]

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
                **assets[exchange_symbol]
            )
            self.assets[exchange_symbol] = asset_obj

    @abstractmethod
    def subscribe_to_market_data(self, symbol):
        pass

    @abstractproperty
    def positions(self):
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
        pass

    @abc.abstractmethod
    def tickers(self, date, pairs):
        return
