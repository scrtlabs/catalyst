import abc
import re
from abc import ABCMeta, abstractmethod, abstractproperty
from datetime import timedelta
from time import sleep

import numpy as np
import pandas as pd
from catalyst.assets._assets import TradingPair
from logbook import Logger

from catalyst.data.data_portal import BASE_FIELDS
from catalyst.exchange.bundle_utils import get_start_dt, \
    get_delta, get_periods, get_adj_dates
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.exchange_errors import MismatchingBaseCurrencies, \
    InvalidOrderStyle, BaseCurrencyNotFoundError, SymbolNotFoundOnExchange, \
    InvalidHistoryFrequencyError, MismatchingFrequencyError, \
    BundleNotFoundError, NoDataAvailableOnExchange
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
        self.assets = {}
        self._portfolio = None
        self.minute_writer = None
        self.minute_reader = None
        self.base_currency = None

        self.num_candles_limit = None
        self.max_requests_per_minute = None
        self.request_cpt = None
        self.bundle = ExchangeBundle(self)

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

    def ask_request(self):
        """
        Asks permission to issue a request to the exchange.
        The primary purpose is to avoid hitting rate limits.

        The application will pause if the maximum requests per minute
        permitted by the exchange is exceeded.

        :return boolean:

        """
        now = pd.Timestamp.utcnow()
        if not self.request_cpt:
            self.request_cpt = dict()
            self.request_cpt[now] = 0
            return True

        cpt_date = self.request_cpt.keys()[0]
        cpt = self.request_cpt[cpt_date]

        if now > cpt_date + timedelta(minutes=1):
            self.request_cpt = dict()
            self.request_cpt[now] = 0
            return True

        if cpt >= self.max_requests_per_minute:
            delta = now - cpt_date

            sleep_period = 60 - delta.total_seconds()
            sleep(sleep_period)

            now = pd.Timestamp.utcnow()
            self.request_cpt = dict()
            self.request_cpt[now] = 0
            return True
        else:
            self.request_cpt[cpt_date] += 1

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
                             (asset['symbol'], self.name.title()))

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

    def get_assets(self, symbols=None):
        assets = []

        if symbols is not None:
            for symbol in symbols:
                asset = self.get_asset(symbol)
                assets.append(asset)
        else:
            for key in self.assets:
                assets.append(self.assets[key])

        return assets

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
            supported_symbols = [pair.symbol.encode('utf-8') for pair in
                                 self.assets.values()]
            raise SymbolNotFoundOnExchange(
                symbol=symbol,
                exchange=self.name.title(),
                supported_symbols=supported_symbols
            )

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

            if 'min_trade_size' in asset:
                min_trade_size = asset['min_trade_size']
            else:
                min_trade_size = 0.0000001

            if 'end_daily' in asset and asset['end_daily'] != 'N/A':
                end_daily = pd.to_datetime(asset['end_daily'], utc=True)
            else:
                end_daily = None

            if 'end_minute' in asset and asset['end_minute'] != 'N/A':
                end_minute = pd.to_datetime(asset['end_minute'], utc=True)
            else:
                end_minute = None

            trading_pair = TradingPair(
                symbol=asset['symbol'],
                exchange=self.name,
                start_date=start_date,
                end_date=end_date,
                leverage=leverage,
                asset_name=asset_name,
                min_trade_size=min_trade_size,
                end_daily=end_daily,
                end_minute=end_minute,
                exchange_symbol=exchange_symbol
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
            raise KeyError('Invalid column: {}'.format(field))

        values = []
        for asset in assets:
            value = self.get_single_spot_value(asset, field, data_frequency)
            values.append(value)

        return values

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

        ohlc = self.get_candles(data_frequency, asset)
        if field not in ohlc:
            raise KeyError('Invalid column: %s' % field)

        value = ohlc[field]
        log.debug('got spot value: {}'.format(value))

        return value

    def get_series_from_bundle(self, assets, start_dt, end_dt, data_frequency,
                               field):
        """

        :return:
        """
        reader = self.bundle.get_reader(data_frequency)

        if reader is None:
            raise BundleNotFoundError(
                exchange=self.name.title(),
                data_frequency=data_frequency
            )

        series = dict()
        try:
            arrays = reader.load_raw_arrays(
                sids=[asset.sid for asset in assets],
                fields=[field],
                start_dt=start_dt,
                end_dt=end_dt
            )

            periods = self.bundle.get_calendar_periods_range(
                start_dt, end_dt, data_frequency
            )

            for asset_index, asset in enumerate(assets):
                asset_values = arrays[asset_index]

                value_series = pd.Series(asset_values[0], index=periods)
                series[asset] = value_series

        except Exception as e:
            log.debug('unable to retrieve from bundle: {}'.format(e))

        return series

    def get_series_from_candles(self, candles, start_dt, end_dt,
                                field, previous_value=None):
        """
        Get a series of field data for the specified candles.

        :param candles:
        :param start_dt:
        :param end_dt:
        :param field:
        :param previous_value:
        :return:
        """

        dates = [candle['last_traded'] for candle in candles]
        values = [candle[field] for candle in candles]

        periods = pd.date_range(start_dt, end_dt)
        series = pd.Series(values, index=dates)

        series.reindex(periods, method='ffill', fill_value=previous_value)

        return series

    def get_history_window(self,
                           assets,
                           end_dt,
                           bar_count,
                           frequency,
                           field,
                           data_frequency=None,
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

        freq_match = re.match(r'([0-9].*)(m|M|d|D)', frequency, re.M | re.I)
        if freq_match:
            candle_size = int(freq_match.group(1))
            unit = freq_match.group(2)

        else:
            raise InvalidHistoryFrequencyError(frequency)

        if unit.lower() == 'd':
            if data_frequency == 'minute':
                data_frequency = 'daily'

        elif unit.lower() == 'm':
            # if data_frequency != 'minute':
            # raise MismatchingFrequencyError(
            #     frequency=frequency,
            #     data_frequency=data_frequency
            # )
            if data_frequency == 'daily':
                data_frequency = 'minute'

        else:
            raise InvalidHistoryFrequencyError(frequency)

        adj_bar_count = candle_size * bar_count
        start_dt = get_start_dt(end_dt, adj_bar_count, data_frequency)

        try:
            adj_start_dt, adj_end_dt = get_adj_dates(
                start_dt, end_dt, assets, data_frequency
            )
            in_bundle = True

        except NoDataAvailableOnExchange:
            in_bundle = False

        if in_bundle:
            missing_assets = self.bundle.filter_existing_assets(
                assets=assets,
                start_dt=adj_start_dt,
                end_dt=adj_end_dt,
                data_frequency=data_frequency
            )

            if missing_assets:
                self.bundle.ingest_assets(
                    assets=assets,
                    start_dt=adj_start_dt,
                    end_dt=adj_end_dt,
                    data_frequency=data_frequency
                )

            series = self.get_series_from_bundle(
                assets=assets,
                start_dt=adj_start_dt,
                end_dt=adj_end_dt,
                data_frequency=data_frequency,
                field=field
            )

        else:
            series = dict()

        for asset in assets:
            if asset not in series or series[asset].index[-1] < end_dt:
                # Adding bars too recent to be contained in the consolidated
                # exchanges bundles. We go directly against the exchange
                # to retrieve the candles.

                trailing_dt = \
                    series[asset].index[-1] + get_delta(1, data_frequency) \
                        if asset in series else start_dt

                trailing_bar_count = \
                    get_periods(trailing_dt, end_dt, data_frequency)

                # The get_history method supports multiple asset
                candles = self.get_candles(
                    data_frequency=data_frequency,
                    assets=asset,
                    bar_count=trailing_bar_count,
                    end_dt=end_dt
                )

                last_value = series[asset].iloc(0) if asset in series \
                    else np.nan

                candle_series = self.get_series_from_candles(
                    candles=candles,
                    start_dt=trailing_dt,
                    end_dt=end_dt,
                    field=field,
                    previous_value=last_value
                )

                if asset in series:
                    series[asset].append(candle_series)

                else:
                    series[asset] = candle_series

        df = pd.DataFrame(series)

        if candle_size > 1:
            if field == 'open':
                agg = 'first'
            elif field == 'high':
                agg = 'max'
            elif field == 'low':
                agg = 'min'
            elif field == 'close':
                agg = 'last'
            elif field == 'volume':
                agg = 'sum'
            else:
                raise ValueError('Invalid field.')

            df = df.resample('{}T'.format(candle_size)).agg(agg)

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
                exchange=self.name.title()
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
            raise InvalidOrderStyle(exchange=self.name.title(),
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
        if order:
            self._portfolio.create_order(order)
            return order.id
        else:
            return None

    # The methods below must be implemented for each exchange.
    @abstractmethod
    def get_balances(self):
        """
        Retrieve wallet balances for the exchange
        :return balances: A dict of currency => available balance
        """
        pass

    @abstractmethod
    def create_order(self, asset, amount, is_buy, style):
        """
        Place an order on the exchange.

        :param asset : Asset
            The asset that this order is for.
        :param amount : int
            The amount of shares to order. If ``amount`` is positive, this is
            the number of shares to buy or cover. If ``amount`` is negative,
            this is the number of shares to sell or short.
        :param style : ExecutionStyle
            The execution style for the order.
        :param is_buy: boolean
            Is it a buy order?
        :return:
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
    def get_candles(self, data_frequency, assets, bar_count=None,
                    start_dt=None, end_dt=None):
        """
        Retrieve OHLCV candles for the given assets

        :param data_frequency:
            The candle frequency: minute or daily
        :param assets: list[TradingPair]
            The targeted assets.
        :param bar_count:
            The number of bar desired. (default 1)
        :param end_dt: datetime, optional
            The last bar date.
        :param start_dt: datetime, optional
            The first bar date.

        :return dict[TradingPair, dict[str, Object]]: OHLCV data
            A dictionary of OHLCV candles. Each TradingPair instance is
            mapped to a list of dictionaries with this structure:
                open: float
                high: float
                low: float
                close: float
                volume: float
                last_traded: datetime

            See definition here:
                http://www.investopedia.com/terms/o/ohlcchart.asp
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

    @abc.abstractmethod
    def get_orderbook(self, asset, order_type):
        """
        Retrieve the the orderbook for the given trading pair.

        :param asset: TradingPair
        :param order_type: str
            The type of orders: bid, ask or all

        :return:
        """
        pass
