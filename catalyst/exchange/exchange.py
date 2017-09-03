import abc
import collections
import random
from abc import ABCMeta, abstractmethod, abstractproperty
from time import sleep

import numpy as np
import pandas as pd
from catalyst.assets._assets import TradingPair
from logbook import Logger

from catalyst.data.data_portal import BASE_FIELDS
from catalyst.errors import (
    SymbolNotFound,
)
from catalyst.exchange.exchange_errors import MismatchingBaseCurrencies, \
    InvalidOrderStyle, BaseCurrencyNotFoundError
from catalyst.exchange.exchange_execution import ExchangeStopLimitOrder, \
    ExchangeLimitOrder, ExchangeStopOrder
from catalyst.exchange.exchange_portfolio import ExchangePortfolio
from catalyst.exchange.exchange_utils import get_exchange_symbols
from catalyst.finance.order import ORDER_STATUS
from catalyst.finance.transaction import Transaction

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
        self.base_currency = None

    @property
    def positions(self):
        return self.portfolio.positions

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
            self.synchronize_portfolio()

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
            raise SymbolNotFound(symbol=symbol)

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

            if 'start_date' in asset:
                start_date = pd.to_datetime(asset['start_date'], utc=True)
            else:
                start_date = None

            if 'end_date' in asset:
                end_date = pd.to_datetime(asset['end_date'], utc=True)
            else:
                end_date = None

            if 'leverage' in asset:
                leverage = asset['leverage']
            else:
                leverage = 1.0

            if 'asset_name' in asset:
                asset_name = asset['asset_name']
            else:
                asset_name = None

            trading_pair = TradingPair(
                symbol=asset['symbol'],
                exchange=self.name,
                start_date=start_date,
                end_date=end_date,
                leverage=leverage,
                asset_name=asset_name
            )

            self.assets[exchange_symbol] = trading_pair

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

        series = dict()
        for asset in assets:
            asset_candles = candles[asset]

            values = map(lambda candle: candle[field], asset_candles)
            dates = map(lambda candle: candle['last_traded'], asset_candles)

            value_series = pd.Series(values, index=dates)
            series[asset] = value_series

        df = pd.concat(series)
        return df

    def synchronize_portfolio(self):
        """
        Update the portfolio cash and position balances based on the
        latest ticker prices.

        :return:
        """
        log.debug('synchronizing portfolio with exchange {}'.format(self.name))
        balances = self.get_balances()

        base_position_available = balances[self.base_currency] \
            if self.base_currency in balances else None

        if base_position_available is None:
            raise BaseCurrencyNotFoundError(
                base_currency=self.base_currency,
                exchange=self.name
            )

        portfolio = self._portfolio
        portfolio.cash = base_position_available
        log.debug('found base currency balance: {}'.format(portfolio.cash))

        if portfolio.starting_cash is None:
            portfolio.starting_cash = portfolio.cash

        if portfolio.positions:
            assets = portfolio.positions.keys()
            tickers = self.tickers(assets)

            portfolio.positions_value = 0.0
            for asset in tickers:
                # TODO: convert if the position is not in the base currency
                ticker = tickers[asset]
                position = portfolio.positions[asset]
                position.last_sale_price = ticker['last_price']
                position.last_sale_date = ticker['timestamp']

                portfolio.positions_value += \
                    position.amount * position.last_sale_price
                portfolio.portfolio_value = \
                    portfolio.positions_value + portfolio.cash

    @abstractmethod
    def get_balances(self):
        """
        Retrieve wallet balances for the exchange
        :return balances: A dict of currency => available balance
        """
        pass

    @abstractmethod
    def create_order(self, asset, amount, is_buy, style):
        pass

    def order(self, asset, amount, limit_price=None, stop_price=None,
              style=None):
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
        if amount == 0:
            log.warn('skipping order amount of 0')
            return None

        if asset.base_currency != self.base_currency.lower():
            raise MismatchingBaseCurrencies(
                base_currency=asset.base_currency,
                algo_currency=self.base_currency
            )

        is_buy = (amount > 0)

        if limit_price is not None and stop_price is not None:
            style = ExchangeStopLimitOrder(limit_price, stop_price,
                                           exchange=self.name)
        elif limit_price is not None:
            style = ExchangeLimitOrder(limit_price, exchange=self.name)

        elif stop_price is not None:
            style = ExchangeStopOrder(stop_price, exchange=self.name)

        elif style is not None:
            raise InvalidOrderStyle(exchange=self.name,
                                    style=style.__class__.__name__)
        else:
            raise ValueError('Incomplete order data.')

        display_price = limit_price if limit_price is not None else stop_price
        log.debug(
            'issuing {side} order of {amount} {symbol} for {type}: {price}'.format(
                side='buy' if is_buy else 'sell',
                amount=amount,
                symbol=asset.symbol,
                type=style.__class__.__name__,
                price='{}{}'.format(display_price, asset.base_currency)
            )
        )
        order = self.create_order(asset, amount, is_buy, style)

        self._portfolio.create_order(order)

        return order.id

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
