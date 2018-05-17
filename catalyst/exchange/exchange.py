import abc
from abc import ABCMeta, abstractmethod, abstractproperty
from datetime import timedelta
from time import sleep

import numpy as np
import pandas as pd
from catalyst.constants import LOG_LEVEL
from catalyst.data.data_portal import BASE_FIELDS
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.exchange_errors import MismatchingQuoteCurrencies, \
    SymbolNotFoundOnExchange, \
    PricingDataNotLoadedError, \
    NoDataAvailableOnExchange, NoValueForField, \
    NoCandlesReceivedFromExchange, \
    TickerNotFoundError, NotEnoughCashError
from catalyst.exchange.utils.datetime_utils import get_delta, \
    get_periods_range, \
    get_periods, get_start_dt, get_frequency, \
    get_candles_number_from_minutes
from catalyst.exchange.utils.exchange_utils import get_exchange_symbols, \
    resample_history_df, has_bundle, get_candles_df
from logbook import Logger

log = Logger('Exchange', level=LOG_LEVEL)


class Exchange:
    __metaclass__ = ABCMeta

    MIN_MINUTES_REQUESTED = 150

    def __init__(self):
        self.name = None
        self.assets = []
        self._symbol_maps = [None, None]
        self.minute_writer = None
        self.minute_reader = None
        self.quote_currency = None

        self.num_candles_limit = None
        self.max_requests_per_minute = None
        self.request_cpt = None
        self.bundle = ExchangeBundle(self.name)

        self.low_balance_threshold = None

    @abstractproperty
    def account(self):
        pass

    @abstractproperty
    def time_skew(self):
        pass

    def has_bundle(self, data_frequency):
        return has_bundle(self.name, data_frequency)

    def is_open(self, dt):
        """
        Is the exchange open

        Parameters
        ----------
        dt: Timestamp

        Returns
        -------
        bool

        """
        # TODO: implement for each exchange.
        return True

    def ask_request(self):
        """
        Asks permission to issue a request to the exchange.
        The primary purpose is to avoid hitting rate limits.

        The application will pause if the maximum requests per minute
        permitted by the exchange is exceeded.

        Returns
        -------
        bool

        """
        now = pd.Timestamp.utcnow()
        if not self.request_cpt:
            self.request_cpt = dict()
            self.request_cpt[now] = 0
            return True

        cpt_date = list(self.request_cpt.keys())[0]
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
        The exchange specific symbol of the specified market.

        Parameters
        ----------
        asset: TradingPair

        Returns
        -------
        str

        """
        symbol = None

        for a in self.assets:
            if not symbol and a.symbol == asset.symbol:
                symbol = a.symbol

        if not symbol:
            raise ValueError('Currency %s not supported by exchange %s' %
                             (asset['symbol'], self.name.title()))

        return symbol

    def get_symbols(self, assets):
        """
        Get a list of symbols corresponding to each given asset.

        Parameters
        ----------
        assets: list[TradingPair]

        Returns
        -------
        list[str]

        """
        symbols = []
        for asset in assets:
            symbols.append(self.get_symbol(asset))

        return symbols

    def get_assets(self, symbols=None, data_frequency=None,
                   is_exchange_symbol=False,
                   is_local=None, quote_currency=None):
        """
        The list of markets for the specified symbols.

        Parameters
        ----------
        symbols: list[str]
        data_frequency: str
        is_exchange_symbol: bool
        is_local: bool

        Returns
        -------
        list[TradingPair]
            A list of asset objects.

        Notes
        -----
        See get_asset for details of each parameter.

        """
        if symbols is None:
            # Make a distinct list of all symbols
            symbols = list(set([asset.symbol for asset in self.assets]))
            symbols.sort()

            if quote_currency is not None:
                for symbol in symbols[:]:
                    suffix = '_{}'.format(quote_currency.lower())

                    if not symbol.endswith(suffix):
                        symbols.remove(symbol)

            is_exchange_symbol = False

        assets = []
        for symbol in symbols:
            try:
                asset = self.get_asset(
                    symbol, data_frequency, is_exchange_symbol, is_local
                )
                assets.append(asset)

            except SymbolNotFoundOnExchange as e:
                log.warn(e)
        return assets

    def get_asset(self, symbol, data_frequency=None, is_exchange_symbol=False,
                  is_local=None):
        """
        The market for the specified symbol.

        Parameters
        ----------
        symbol: str
            The Catalyst or exchange symbol.

        data_frequency: str
            Check for asset corresponding to the specified data_frequency.
            The same asset might exist in the Catalyst repository or
            locally (following a CSV ingestion). Filtering by
            data_frequency picks the right asset.

        is_exchange_symbol: bool
            Whether the symbol uses the Catalyst or exchange convention.

        is_local: bool
            For the local or Catalyst asset.

        Returns
        -------
        TradingPair
            The asset object.

        """
        asset = None

        # TODO: temp mapping, fix to use a single symbol convention
        og_symbol = symbol
        symbol = self.get_symbol(symbol) if not is_exchange_symbol else symbol
        log.debug(
            'searching assets for: {} {}'.format(
                self.name, symbol
            )
        )
        # TODO: simplify and loose the loop
        for a in self.assets:
            if asset is not None:
                break

            if is_local is not None:
                data_source = 'local' if is_local else 'catalyst'
                applies = (a.data_source == data_source)

            elif data_frequency is not None:
                applies = (
                        (
                                data_frequency == 'minute' and
                                a.end_minute is not None)
                        or (
                                data_frequency == 'daily' and a.end_daily is not None)
                )

            else:
                applies = True

            # The symbol provided may use the Catalyst or the exchange
            # convention
            key = a.exchange_symbol if \
                is_exchange_symbol else self.get_symbol(a)
            if not asset and key.lower() == symbol.lower():
                if applies:
                    asset = a

                else:
                    raise NoDataAvailableOnExchange(
                        symbol=key,
                        exchange=self.name,
                        data_frequency=data_frequency,
                    )

        if asset is None:
            supported_symbols = sorted([a.symbol for a in self.assets])

            raise SymbolNotFoundOnExchange(
                symbol=og_symbol,
                exchange=self.name.title(),
                supported_symbols=supported_symbols
            )

        log.debug('found asset: {}'.format(asset))
        return asset

    def fetch_symbol_map(self, is_local=False):
        index = 1 if is_local else 0
        if self._symbol_maps[index] is not None:
            return self._symbol_maps[index]

        else:
            symbol_map = get_exchange_symbols(self.name, is_local)
            self._symbol_maps[index] = symbol_map
            return symbol_map

    @abstractmethod
    def init(self):
        """
        Load the asset list from the network.

        Returns
        -------

        """

    @abstractmethod
    def load_assets(self, is_local=False):
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

        This method can be omerridden if an exchange offers equivalent data
        via its api.

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
            raise KeyError('Invalid column: {}'.format(field))

        tickers = self.tickers(assets)
        if field == 'close' or field == 'price':
            return [tickers[asset]['last'] for asset in tickers]

        elif field == 'volume':
            return [tickers[asset]['volume'] for asset in tickers]

        else:
            raise NoValueForField(field=field)

    def get_single_spot_value(self, asset, field, data_frequency):
        """
        Similar to 'get_spot_value' but for a single asset

        Notes
        -----
        We're writing each minute bar to disk using zipline's machinery.
        This is especially useful when running multiple algorithms
        concurrently. By using local data when possible, we try to reaching
        request limits on exchanges.

        Parameters
        ----------
        asset: TradingPair
        field: str
        data_frequency: str

        Returns
        -------
        float
            The spot value of the given asset / field

        """
        log.debug(
            'fetching spot value {field} for symbol {symbol}'.format(
                symbol=asset.symbol,
                field=field
            )
        )

        freq = '1T' if data_frequency == 'minute' else '1D'
        ohlc = self.get_candles(freq, asset)
        if field not in ohlc:
            raise KeyError('Invalid column: %s' % field)

        value = ohlc[field]
        log.debug('got spot value: {}'.format(value))

        return value

    # TODO: replace with catalyst.exchange.exchange_utils.get_candles_df
    def get_series_from_candles(self, candles, start_dt, end_dt,
                                data_frequency, field, previous_value=None):
        """
        Get a series of field data for the specified candles.

        Parameters
        ----------
        candles: list[dict[str, float]]
        start_dt: datetime
        end_dt: datetime
        data_frequency: str
        field: str
        previous_value: float

        Returns
        -------
        Series

        """
        dates = [candle['last_traded'] for candle in candles]
        values = [candle[field] for candle in candles]
        series = pd.Series(values, index=dates)

        periods = get_periods_range(
            start_dt=start_dt, end_dt=end_dt, freq=data_frequency
        )
        # TODO: ensure that this working as expected, if not use fillna
        series = series.reindex(
            periods,
            method='ffill',
            fill_value=previous_value,
        )
        series.sort_index(inplace=True)
        return series

    def get_history_window(self,
                           assets,
                           end_dt,
                           bar_count,
                           frequency,
                           field,
                           data_frequency=None,
                           is_current=False):

        """
        Public API method that returns a dataframe containing the requested
        history window.  Data is fully adjusted.

        Parameters
        ----------
        assets : list[TradingPair]
            The assets whose data is desired.

        end_dt: datetime
            The date of the last bar

        bar_count: int
            The number of bars desired.

        frequency: string
            "1d" or "1m"

        field: string
            The desired field of the asset.

        data_frequency: string
            The frequency of the data to query; i.e. whether the data is
            'daily' or 'minute' bars.

        is_current: bool
            Skip date filters when current data is requested (last few bars
            until now).

        Notes
        -----
        Catalysts requires an end data with bar count both CCXT wants a
        start data with bar count. Since we have to make calculations here,
        we ensure that the last candle match the end_dt parameter.

        Returns
        -------
        DataFrame
            A dataframe containing the requested data.

        """
        freq, candle_size, unit, data_frequency = get_frequency(
            frequency, data_frequency, supported_freqs=['T', 'D', 'H']
        )

        # we want to avoid receiving empty candles
        # so we request more than needed
        # TODO: consider defining a const per asset
        # and/or some retry mechanism (in each iteration request more data)
        min_candles_number = get_candles_number_from_minutes(
            unit,
            candle_size,
            self.MIN_MINUTES_REQUESTED)

        requested_bar_count = bar_count

        if requested_bar_count < min_candles_number:
            requested_bar_count = min_candles_number

        # The get_history method supports multiple asset
        candles = self.get_candles(
            freq=freq,
            assets=assets,
            bar_count=requested_bar_count,
            end_dt=end_dt if not is_current else None,
        )

        # candles sanity check - verify no empty candles were received:
        for asset in candles:
            if not candles[asset]:
                raise NoCandlesReceivedFromExchange(
                    bar_count=requested_bar_count,
                    end_dt=end_dt,
                    asset=asset,
                    exchange=self.name)

        # for avoiding unnecessary forward fill end_dt is taken back one second
        forward_fill_till_dt = end_dt - timedelta(seconds=1)

        series = get_candles_df(candles=candles,
                                field=field,
                                freq=frequency,
                                bar_count=requested_bar_count,
                                end_dt=forward_fill_till_dt)

        # TODO: consider how to approach this edge case
        # delta_candle_size = candle_size * 60 if unit == 'H' else candle_size
        # Checking to make sure that the dates match
        # delta = get_delta(delta_candle_size, data_frequency)
        # adj_end_dt = end_dt - delta
        # last_traded = asset_series.index[-1]
        # if last_traded < adj_end_dt:
        #    raise LastCandleTooEarlyError(
        #        last_traded=last_traded,
        #        end_dt=adj_end_dt,
        #        exchange=self.name,
        #    )

        df = pd.DataFrame(series)
        df.dropna(inplace=True)

        return df.tail(bar_count)

    def get_history_window_with_bundle(self,
                                       assets,
                                       end_dt,
                                       bar_count,
                                       frequency,
                                       field,
                                       data_frequency=None,
                                       ffill=True,
                                       force_auto_ingest=False):

        """
        Public API method that returns a dataframe containing the requested
        history window.  Data is fully adjusted.

        Parameters
        ----------
        assets : list[TradingPair]
            The assets whose data is desired.

        end_dt: datetime
            The date of the last bar.

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
        DataFrame
            A dataframe containing the requested data.

        """
        # TODO: this function needs some work,
        # we're currently using it just for benchmark data
        freq, candle_size, unit, data_frequency = get_frequency(
            frequency, data_frequency, supported_freqs=['T', 'D']
        )
        adj_bar_count = candle_size * bar_count
        try:
            series = self.bundle.get_history_window_series_and_load(
                assets=assets,
                end_dt=end_dt,
                bar_count=adj_bar_count,
                field=field,
                data_frequency=data_frequency,
                force_auto_ingest=force_auto_ingest
            )

        except (PricingDataNotLoadedError, NoDataAvailableOnExchange):
            series = dict()

        for asset in assets:
            if asset not in series or series[asset].index[-1] < end_dt:
                # Adding bars too recent to be contained in the consolidated
                # exchanges bundles. We go directly against the exchange
                # to retrieve the candles.
                start_dt = get_start_dt(end_dt, adj_bar_count, data_frequency)
                trailing_dt = \
                    series[asset].index[-1] + get_delta(1, data_frequency) \
                        if asset in series else start_dt

                # The get_history method supports multiple asset
                # Use the original frequency to let each api optimize
                # the size of result sets
                trailing_bars = get_periods(
                    trailing_dt, end_dt, freq
                )
                candles = self.get_candles(
                    freq=freq,
                    assets=asset,
                    end_dt=end_dt,
                    bar_count=trailing_bars if trailing_bars < 500 else 500,
                )

                last_value = series[asset].iloc(0) if asset in series \
                    else np.nan

                # Create a series with the common data_frequency, ffill
                # missing values
                candle_series = self.get_series_from_candles(
                    candles=candles,
                    start_dt=trailing_dt,
                    end_dt=end_dt,
                    data_frequency=data_frequency,
                    field=field,
                    previous_value=last_value
                )

                if asset in series:
                    series[asset].append(candle_series)

                else:
                    series[asset] = candle_series

        df = resample_history_df(pd.DataFrame(series), freq, field)
        # TODO: consider this more carefully
        df.dropna(inplace=True)

        return df

    def _check_low_balance(self, currency, balances, amount):
        """
        In order to avoid spending money that the user doesn't own,
        we are comparing to the balance on the account.
        :param currency: str
        :param balances: dict
        :param amount: float
        :return: free: float,
                       bool
        """
        free = balances[currency]['free'] if currency in balances else 0.0

        if free < amount:
            return free, True

        else:
            return free, False

    def _check_position_balance(self, currency, balances, amount):
        """
        In order to avoid spending money that the user doesn't own,
        we are comparing to the balance on the account.
        For positions, we want to avoid double updates, since, exchanges
        update positions when the order is opened as used, catalyst wants
        to take them into consideration, therefore running comparison on total.
        :param currency: str
        :param balances: dict
        :param amount: float
        :return: total: float,
                        bool
        """
        total = balances[currency]['total'] if currency in balances else 0.0

        if total < amount:
            return total, True

        else:
            return total, False

    def sync_positions(self, positions, cash=None,
                       check_balances=False):
        """
        Update the portfolio cash and position balances based on the
        latest ticker prices.

        Parameters
        ----------
        positions:
            The positions to synchronize.

        check_balances:
            Check balances amounts against the exchange.

        """
        free_cash = 0.0
        if check_balances:
            log.debug('fetching {} balances'.format(self.name))
            balances = self.get_balances()
            log.debug(
                'got free balances for {} currencies'.format(
                    len(balances)
                )
            )
            if cash is not None:
                free_cash, is_lower = self._check_low_balance(
                    currency=self.quote_currency,
                    balances=balances,
                    amount=cash,
                )
                if is_lower:
                    raise NotEnoughCashError(
                        currency=self.quote_currency,
                        exchange=self.name,
                        free=free_cash,
                        cash=cash,
                    )

        positions_value = 0.0
        if positions:
            assets = list(set([position.asset for position in positions]))
            tickers = self.tickers(assets)

            for position in positions:
                asset = position.asset
                if asset not in tickers:
                    raise TickerNotFoundError(
                        symbol=asset.symbol,
                        exchange=self.name,
                    )

                ticker = tickers[asset]
                log.debug(
                    'updating {symbol} position, last traded on {dt} for '
                    '{price}{currency}'.format(
                        symbol=asset.symbol,
                        dt=ticker['last_traded'],
                        price=ticker['last_price'],
                        currency=asset.quote_currency,
                    )
                )
                position.last_sale_price = ticker['last_price']
                position.last_sale_date = ticker['last_traded']

                if check_balances:
                    total, is_lower = self._check_position_balance(
                        currency=asset.base_currency,
                        balances=balances,
                        amount=position.amount,
                    )

                    if is_lower:
                        log.warn(
                            'detected lower balance for {} on {}: {} < {}, '
                            'updating position amount'.format(
                                asset.symbol, self.name, total, position.amount
                            )
                        )
                        position.amount = total

                positions_value += \
                    position.amount * position.last_sale_price

        return free_cash, positions_value

    def order(self, asset, amount, style):
        """Place an order.

        Parameters
        ----------
        asset : TradingPair
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

        if self.quote_currency is None:
            raise ValueError('no quote_currency defined for this exchange')

        if asset.quote_currency != self.quote_currency.lower():
            raise MismatchingQuoteCurrencies(
                quote_currency=asset.quote_currency,
                algo_currency=self.quote_currency
            )

        is_buy = (amount > 0)
        display_price = style.get_limit_price(is_buy)

        log.debug(
            'issuing {side} order of {amount} {symbol} for {type}:'
            ' {price}'.format(
                side='buy' if is_buy else 'sell',
                amount=amount,
                symbol=asset.symbol,
                type=style.__class__.__name__,
                price='{}{}'.format(display_price, asset.quote_currency)
            )
        )

        return self.create_order(asset, amount, is_buy, style)

    # The methods below must be implemented for each exchange.
    @abstractmethod
    def get_balances(self):
        """
        Retrieve wallet balances for the exchange.

        Returns
        -------
        dict[TradingPair, float]

        """
        pass

    @abstractmethod
    def create_order(self, asset, amount, is_buy, style):
        """
        Place an order on the exchange.

        Parameters
        ----------
        asset: TradingPair
            The target market.

        amount: float
            The amount of shares to order. If ``amount`` is positive, this is
            the number of shares to buy or cover. If ``amount`` is negative,
            this is the number of shares to sell or short.

        is_buy: bool
            Is it a buy order?

        style: ExecutionStyle

        Returns
        -------
        Order

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
    def get_order(self, order_id, symbol_or_asset=None):
        """Lookup an order based on the order id returned from one of the
        order functions.

        Parameters
        ----------
        order_id : str
            The unique identifier for the order.
        symbol_or_asset: str|TradingPair
            The catalyst symbol, some exchanges need this

        Returns
        -------
        order : Order
            The order object.
        execution_price: float
            The execution price per share of the order
        """
        pass

    @abstractmethod
    def process_order(self, order):
        """
        Similar to get_order but looks only for executed orders.

        Parameters
        ----------
        order: Order

        Returns
        -------
        float
            Avg execution price

        """

    @abstractmethod
    def cancel_order(self, order_param,
                     symbol_or_asset=None, params={}):
        """Cancel an open order.

        Parameters
        ----------
        order_param : str or Order
            The order_id or order object to cancel.
        symbol_or_asset: str|TradingPair
            The catalyst symbol, some exchanges need this
        params:
        """
        pass

    @abstractmethod
    def get_candles(self, freq, assets, bar_count, start_dt=None, end_dt=None):
        """
        Retrieve OHLCV candles for the given assets

        Parameters
        ----------
        freq: str
            The frequency alias per convention:
            http://pandas.pydata.org/pandas-docs/stable/timeseries.html#offset-aliases

        assets: list[TradingPair]
            The targeted assets.

        bar_count: int
            The number of bar desired. (default 1)

        end_dt: datetime, optional
            The last bar date.

        start_dt: datetime, optional
            The first bar date.

        Returns
        -------
        dict[TradingPair, dict[str, Object]]
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
    def tickers(self, assets, on_ticker_error='raise'):
        """
        Retrieve current tick data for the given assets

        Parameters
        ----------
        assets: list[TradingPair]
        on_ticker_error: str [raise|warn]
            How to handle an error when retrieving a single ticker.

        Returns
        -------
        list[dict[str, float]

        """
        pass

    @abc.abstractmethod
    def get_account(self):
        """
        Retrieve the account parameters.
        """
        pass

    @abc.abstractmethod
    def get_orderbook(self, asset, order_type, limit):
        """
        Retrieve the orderbook for the given trading pair.

        Parameters
        ----------
        asset: TradingPair
        order_type: str
            The type of orders: bid, ask or all
        limit: int

        Returns
        -------
        list[dict[str, float]
        """
        pass

    @abc.abstractmethod
    def get_trades(self, asset, my_trades, start_dt, limit):
        """
        Retrieve a list of trades.

        Parameters
        ----------
        my_trades: bool
            List only my trades.
        start_dt
        limit

        Returns
        -------

        """
