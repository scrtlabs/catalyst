import copy
import json
import os
import re
from collections import defaultdict

import ccxt
import pandas as pd
import six
from ccxt import InvalidOrder, NetworkError, \
    ExchangeError, RequestTimeout
from logbook import Logger
from six import string_types

from catalyst.algorithm import MarketOrder
from catalyst.assets._assets import TradingPair
from catalyst.constants import LOG_LEVEL
from catalyst.exchange.exchange import Exchange
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.exchange_errors import InvalidHistoryFrequencyError, \
    ExchangeSymbolsNotFound, ExchangeRequestError, InvalidOrderStyle, \
    ExchangeNotFoundError, CreateOrderError, InvalidHistoryTimeframeError, \
    UnsupportedHistoryFrequencyError
from catalyst.exchange.exchange_execution import ExchangeLimitOrder
from catalyst.exchange.utils.exchange_utils import mixin_market_params, \
    get_exchange_folder, get_catalyst_symbol, \
    get_exchange_auth
from catalyst.exchange.utils.datetime_utils import from_ms_timestamp, \
    get_epoch, \
    get_periods_range
from catalyst.finance.order import Order, ORDER_STATUS
from catalyst.finance.transaction import Transaction

log = Logger('CCXT', level=LOG_LEVEL)

SUPPORTED_EXCHANGES = dict(
    binance=ccxt.binance,
    bitfinex=ccxt.bitfinex,
    bittrex=ccxt.bittrex,
    poloniex=ccxt.poloniex,
    bitmex=ccxt.bitmex,
    gdax=ccxt.gdax,
)


class CCXT(Exchange):
    def __init__(self, exchange_name, key,
                 secret, password, quote_currency):
        log.debug(
            'finding {} in CCXT exchanges:\n{}'.format(
                exchange_name, ccxt.exchanges
            )
        )
        try:
            # Making instantiation as explicit as possible for code tracking.
            if exchange_name in SUPPORTED_EXCHANGES:
                exchange_attr = SUPPORTED_EXCHANGES[exchange_name]

            else:
                exchange_attr = getattr(ccxt, exchange_name)

            self.api = exchange_attr({
                'apiKey': key,
                'secret': secret,
                'password': password,
            })
            self.api.enableRateLimit = True

        except Exception:
            raise ExchangeNotFoundError(exchange_name=exchange_name)

        self._symbol_maps = [None, None]

        self.name = exchange_name

        self.quote_currency = quote_currency
        self.transactions = defaultdict(list)

        self.num_candles_limit = 2000
        self.max_requests_per_minute = 60
        self.low_balance_threshold = 0.1
        self.request_cpt = dict()
        self._common_symbols = dict()

        self.bundle = ExchangeBundle(self.name)
        self.markets = None
        self._is_init = False

    def init(self):
        if self._is_init:
            return

        exchange_folder = get_exchange_folder(self.name)
        filename = os.path.join(exchange_folder, 'cctx_markets.json')

        if os.path.exists(filename):
            timestamp = os.path.getmtime(filename)
            dt = pd.to_datetime(timestamp, unit='s', utc=True)

            if dt >= pd.Timestamp.utcnow().floor('1D'):
                with open(filename) as f:
                    self.markets = json.load(f)

                log.debug('loaded markets for {}'.format(self.name))

        if self.markets is None:
            try:
                markets_symbols = self.api.load_markets()
                log.debug(
                    'fetching {} markets:\n{}'.format(
                        self.name, markets_symbols
                    )
                )

                self.markets = self.api.fetch_markets()
                with open(filename, 'w+') as f:
                    json.dump(self.markets, f, indent=4)

            except (ExchangeError, NetworkError) as e:
                log.warn(
                    'unable to fetch markets {}: {}'.format(
                        self.name, e
                    )
                )
                raise ExchangeRequestError(error=e)

        self.load_assets()
        self._is_init = True

    @staticmethod
    def find_exchanges(features=None, is_authenticated=False):
        ccxt_features = []
        if features is not None:
            for feature in features:
                if not feature.endswith('Bundle'):
                    ccxt_features.append(feature)

        exchange_names = []
        for exchange_name in ccxt.exchanges:
            if is_authenticated:
                exchange_auth = get_exchange_auth(exchange_name)

                has_auth = (exchange_auth['key'] != ''
                            and exchange_auth['secret'] != '')

                if not has_auth:
                    continue

            log.debug('loading exchange: {}'.format(exchange_name))
            exchange = getattr(ccxt, exchange_name)()

            if ccxt_features is None:
                has_feature = True

            else:
                try:
                    has_feature = all(
                        [exchange.has[feature] for feature in ccxt_features]
                    )

                except Exception:
                    has_feature = False

            if has_feature:
                try:
                    log.info('initializing {}'.format(exchange_name))
                    exchange_names.append(exchange_name)

                except Exception as e:
                    log.warn(
                        'unable to initialize exchange {}: {}'.format(
                            exchange_name, e
                        )
                    )

        return exchange_names

    def account(self):
        return None

    def time_skew(self):
        return None

    def get_candle_frequencies(self, data_frequency=None):
        frequencies = []
        try:
            for timeframe in self.api.timeframes:
                freq = CCXT.get_frequency(timeframe, raise_error=False)

                # TODO: support all frequencies
                if data_frequency == 'minute' and not freq.endswith('T'):
                    continue

                elif data_frequency == 'hourly' and not freq.endswith('D'):
                    continue

                elif data_frequency == 'daily' and not freq.endswith('D'):
                    continue

                frequencies.append(freq)

        except Exception as e:
            log.warn(
                'candle frequencies not available for exchange {}'.format(
                    self.name
                )
            )

        return frequencies

    def get_market(self, symbol):
        """
        The CCXT market.

        Parameters
        ----------
        symbol:
            The CCXT symbol.

        Returns
        -------
        dict[str, Object]

        """
        s = self.get_symbol(symbol)
        market = next(
            (market for market in self.markets if market['symbol'] == s),
            None,
        )
        return market

    def substitute_currency_code(self, currency, source='catalyst'):
        if source == 'catalyst':
            currency = currency.upper()

            key = self.api.common_currency_code(currency)
            self._common_symbols[key] = currency.lower()
            return key

        else:
            if currency in self._common_symbols:
                return self._common_symbols[currency]

            else:
                return currency.lower()

    def get_symbol(self, asset_or_symbol, source='catalyst'):
        """
        The CCXT symbol.

        Parameters
        ----------
        asset_or_symbol
        source

        Returns
        -------

        """

        if source == 'ccxt':
            if isinstance(asset_or_symbol, string_types):
                parts = asset_or_symbol.split('/')
                base_currency = self.substitute_currency_code(
                    parts[0], source
                )
                quote_currency = self.substitute_currency_code(
                    parts[1], source
                )
                return '{}_{}'.format(base_currency, quote_currency)

            else:
                return asset_or_symbol.symbol

        else:
            symbol = asset_or_symbol if isinstance(
                asset_or_symbol, string_types
            ) else asset_or_symbol.symbol

            parts = symbol.split('_')
            base_currency = self.substitute_currency_code(
                parts[0], source
            )
            quote_currency = self.substitute_currency_code(
                parts[1], source
            )
            return '{}/{}'.format(base_currency, quote_currency)

    @staticmethod
    def map_frequency(value, source='ccxt', raise_error=True):
        """
        Map a frequency value between CCXT and Catalyst

        Parameters
        ----------
        value: str
        source: str
        raise_error: bool

        Returns
        -------

        Notes
        -----
        The Pandas offset aliases supported by Catalyst:
        Alias	Description
        W	weekly frequency
        M	month end frequency
        D	calendar day frequency
        H	hourly frequency
        T, min	minutely frequency

        The CCXT timeframes:
        '1m': '1minute',
        '1h': '1hour',
        '1d': '1day',
        '1w': '1week',
        '1M': '1month',
        '1y': '1year',
        """
        match = re.match(
            r'([0-9].*)?(m|M|d|D|h|H|T|w|W|min)', value, re.M | re.I
        )
        if match:
            candle_size = int(match.group(1)) \
                if match.group(1) else 1

            unit = match.group(2)

        else:
            raise ValueError('Unable to parse frequency or timeframe')

        if source == 'ccxt':
            if unit == 'd':
                result = '{}D'.format(candle_size)

            elif unit == 'm':
                result = '{}T'.format(candle_size)

            elif unit == 'h':
                result = '{}H'.format(candle_size)

            elif unit == 'w':
                result = '{}W'.format(candle_size)

            elif unit == 'M':
                result = '{}M'.format(candle_size)

            elif raise_error:
                raise InvalidHistoryTimeframeError(timeframe=value)

        else:
            if unit == 'D':
                result = '{}d'.format(candle_size)

            elif unit == 'min' or unit == 'T':
                result = '{}m'.format(candle_size)

            elif unit == 'H':
                result = '{}h'.format(candle_size)

            elif unit == 'W':
                result = '{}w'.format(candle_size)

            elif unit == 'M':
                result = '{}M'.format(candle_size)

            elif raise_error:
                raise InvalidHistoryFrequencyError(frequency=value)

        return result

    @staticmethod
    def get_timeframe(freq, raise_error=True):
        """
        The CCXT timeframe from the Catalyst frequency.

        Parameters
        ----------
        freq: str
            The Catalyst frequency (Pandas convention)

        Returns
        -------
        str

        """
        return CCXT.map_frequency(
            freq, source='catalyst', raise_error=raise_error
        )

    @staticmethod
    def get_frequency(timeframe, raise_error=True):
        """
        Test Catalyst frequency from the CCXT timeframe

        Catalyst uses the Pandas offset alias convention:
        http://pandas.pydata.org/pandas-docs/stable/timeseries.html#offset-aliases

        Parameters
        ----------
        timeframe

        Returns
        -------

        """
        return CCXT.map_frequency(
            timeframe, source='ccxt', raise_error=raise_error
        )

    def get_candles(self, freq, assets, bar_count=1, start_dt=None,
                    end_dt=None):
        is_single = (isinstance(assets, TradingPair))
        if is_single:
            assets = [assets]

        symbols = self.get_symbols(assets)
        timeframe = CCXT.get_timeframe(freq)

        if timeframe not in self.api.timeframes:
            freqs = [CCXT.get_frequency(t) for t in self.api.timeframes]
            raise UnsupportedHistoryFrequencyError(
                exchange=self.name,
                freq=freq,
                freqs=freqs,
            )

        if start_dt is not None and end_dt is not None:
            raise ValueError(
                'Please provide either start_dt or end_dt, not both.'
            )

        if start_dt is None:
            if end_dt is None:
                end_dt = pd.Timestamp.utcnow()

            dt_range = get_periods_range(
                end_dt=end_dt,
                periods=bar_count,
                freq=freq,
            )
            start_dt = dt_range[0]

        delta = start_dt - get_epoch()
        since = int(delta.total_seconds()) * 1000

        candles = dict()
        for index, asset in enumerate(assets):
            ohlcvs = self.api.fetch_ohlcv(
                symbol=symbols[index],
                timeframe=timeframe,
                since=since,
                limit=bar_count,
                params={}
            )

            candles[asset] = []
            for ohlcv in ohlcvs:
                candles[asset].append(dict(
                    last_traded=pd.to_datetime(
                        ohlcv[0], unit='ms', utc=True
                    ),
                    open=ohlcv[1],
                    high=ohlcv[2],
                    low=ohlcv[3],
                    close=ohlcv[4],
                    volume=ohlcv[5]
                ))
            candles[asset] = sorted(
                candles[asset], key=lambda c: c['last_traded']
            )

        if is_single:
            return six.next(six.itervalues(candles))

        else:
            return candles

    def _fetch_symbol_map(self, is_local):
        try:
            return self.fetch_symbol_map(is_local)

        except ExchangeSymbolsNotFound:
            return None

    def get_asset_defs(self, market):
        """
        The local and Catalyst definitions of the specified market.

        Parameters
        ----------
        market: dict[str, Object]
            The CCXT market dicts.

        Returns
        -------
        dict[str, Object]
            The asset definition.

        """
        asset_defs = []

        for is_local in (False, True):
            asset_def = self.get_asset_def(market, is_local)
            asset_defs.append((asset_def, is_local))

        return asset_defs

    def get_asset_def(self, market, is_local=False):
        """
        The asset definition (in symbols.json files) corresponding
        to the the specified market.

        Parameters
        ----------
        market: dict[str, Object]
            The CCXT market dict.
        is_local
            Whether to search in local or Catalyst asset definitions.

        Returns
        -------
        dict[str, Object]
            The asset definition.

        """
        exchange_symbol = market['id']

        symbol_map = self._fetch_symbol_map(is_local)
        if symbol_map is not None:
            assets_lower = {k.lower(): v for k, v in symbol_map.items()}
            key = exchange_symbol.lower()

            asset = assets_lower[key] if key in assets_lower else None
            if asset is not None:
                return asset

            else:
                return None

        else:
            return None

    def create_trading_pair(self, market, asset_def=None, is_local=False):
        """
        Creating a TradingPair from market and asset data.

        Parameters
        ----------
        market: dict[str, Object]
        asset_def: dict[str, Object]
        is_local: bool

        Returns
        -------

        """
        data_source = 'local' if is_local else 'catalyst'
        params = dict(
            exchange=self.name,
            data_source=data_source,
            exchange_symbol=market['id'],
        )
        mixin_market_params(self.name, params, market)

        if asset_def is not None:
            params['symbol'] = asset_def['symbol']

            params['start_date'] = asset_def['start_date'] \
                if 'start_date' in asset_def else None

            params['end_date'] = asset_def['end_date'] \
                if 'end_date' in asset_def else None

            params['leverage'] = asset_def['leverage'] \
                if 'leverage' in asset_def else 1.0

            params['asset_name'] = asset_def['asset_name'] \
                if 'asset_name' in asset_def else None

            params['end_daily'] = asset_def['end_daily'] \
                if 'end_daily' in asset_def \
                   and asset_def['end_daily'] != 'N/A' else None

            params['end_minute'] = asset_def['end_minute'] \
                if 'end_minute' in asset_def \
                   and asset_def['end_minute'] != 'N/A' else None

        else:
            params['symbol'] = get_catalyst_symbol(market)
            # TODO: add as an optional column
            params['leverage'] = 1.0

        return TradingPair(**params)

    def load_assets(self):
        log.debug('loading assets for {}'.format(self.name))
        self.assets = []

        for market in self.markets:
            if 'id' not in market:
                log.warn('invalid market: {}'.format(market))
                continue

            asset_defs = self.get_asset_defs(market)

            asset = None
            for asset_def in asset_defs:
                if asset_def[0] is not None or not asset_defs[1]:
                    try:
                        asset = self.create_trading_pair(
                            market=market,
                            asset_def=asset_def[0],
                            is_local=asset_def[1]
                        )
                        self.assets.append(asset)

                    except TypeError as e:
                        log.warn('unable to add asset: {}'.format(e))

            if asset is None:
                asset = self.create_trading_pair(market=market)
                self.assets.append(asset)

    def get_balances(self):
        try:
            log.debug('retrieving wallets balances')
            balances = self.api.fetch_balance()

            balances_lower = dict()
            for key in balances:
                balances_lower[key.lower()] = balances[key]

        except (ExchangeError, NetworkError) as e:
            log.warn(
                'unable to fetch balance {}: {}'.format(
                    self.name, e
                )
            )
            raise ExchangeRequestError(error=e)

        return balances_lower

    def _create_order(self, order_status):
        """
        Create a Catalyst order object from a CCXT order dictionary

        Parameters
        ----------
        order_status: dict[str, Object]
            The order dict from the CCXT api.

        Returns
        -------
        Order
            The Catalyst order object

        """
        order_id = order_status['id']
        symbol = self.get_symbol(order_status['symbol'], source='ccxt')
        asset = self.get_asset(symbol)

        s = order_status['status']
        amount = order_status['amount']
        filled = order_status['filled']

        if s == 'canceled' or (s == 'closed' and filled == 0):
            status = ORDER_STATUS.CANCELLED

        elif s == 'closed' and filled > 0:
            if filled < amount:
                log.warn(
                    'order {id} is executed but only partially filled:'
                    ' {filled} {symbol} out of {amount}'.format(
                        id=order_status['status'],
                        filled=order_status['filled'],
                        symbol=asset.symbol,
                        amount=order_status['amount'],
                    )
                )
            else:
                log.info(
                    'order {id} executed in full: {filled} {symbol}'.format(
                        id=order_id,
                        filled=filled,
                        symbol=asset.symbol,
                    )
                )

            status = ORDER_STATUS.FILLED

        elif s == 'open':
            status = ORDER_STATUS.OPEN

        elif filled > 0:
            log.info(
                'order {id} partially filled: {filled} {symbol} out of '
                '{amount}, waiting for complete execution'.format(
                    id=order_id,
                    filled=filled,
                    symbol=asset.symbol,
                    amount=amount,
                )
            )
            status = ORDER_STATUS.OPEN

        else:
            log.warn(
                'invalid state {} for order {}'.format(
                    s, order_id
                )
            )
            status = ORDER_STATUS.OPEN

        if order_status['side'] == 'sell':
            amount = -amount
            filled = -filled

        price = order_status['price']
        order_type = order_status['type']

        limit_price = price if order_type == 'limit' else None

        executed_price = order_status['cost'] / order_status['amount']
        commission = order_status['fee']
        date = from_ms_timestamp(order_status['timestamp'])

        order = Order(
            dt=date,
            asset=asset,
            amount=amount,
            stop=None,
            limit=limit_price,
            filled=filled,
            id=order_id,
            commission=commission
        )
        order.status = status

        return order, executed_price

    def _check_order_found(self, previous_orders):
        """
        check if .orders was updated after the fetch api method was called
        and if so extract the new order which should be returned to the user

        :param previous_orders: dict(dict())
        :return: order: Order if an order was found, otherwise, None
        """
        if len(previous_orders) != len(self.api.orders):
            new_orders = [self.api.orders[order_id] for order_id in
                          set(self.api.orders) - set(previous_orders)]
            if len(new_orders) != 1:
                # todo handle this case (not sure we ever will get to this
                # case, since we assume that in this period of
                # time, max 1 order was opened)
                log.warn(
                    "multiple orders were found: : {} "
                    "only the first is considered".format(
                        [x.id for x in new_orders])
                )

            return new_orders[0]

        return None

    def _fetch_missing_order(self, dt_before, symbol):
        """
        check if order was created by running through
        all api functions according to ccxt manual

        :param dt_before: pd.Timestamp
        :return: order: Order/ order_id: str
                if an order was found, otherwise None
        """

        missing_order = None
        previous_orders = copy.deepcopy(self.api.orders)

        if 'fetchOrders' in self.api.has and \
                self.api.has['fetchOrders'] is True:
            # contains all orders, therefore,
            # if method available for this exchange,
            # it's enough to check it.
            self.api.fetch_orders()
            missing_order = self._check_order_found(previous_orders)

        else:
            if 'fetchOpenOrders' in self.api.has and \
                    self.api.has['fetchOpenOrders'] is True:
                self.api.fetch_open_orders()
                missing_order = self._check_order_found(previous_orders)

            if missing_order is None and \
                    'fetchClosedOrders' in self.api.has and \
                    self.api.has['fetchClosedOrders'] is True:
                self.api.fetch_closed_orders()
                missing_order = self._check_order_found(previous_orders)

        if missing_order is None and self.api.has['fetchMyTrades']:
            recent_trades = [x for x in self.api.fetch_my_trades(symbol=symbol)
                             if pd.Timestamp(x['datetime']) > dt_before
                             ]
            missing_order_id_by_trade = list(set(
                trade['order'] for trade in recent_trades
                if trade['order'] not in list(self.api.orders)
            ))
            if missing_order_id_by_trade:
                if len(missing_order_id_by_trade) > 1:
                    # todo handle this case (not sure we ever will get to this
                    # case, since we assume that in this period of
                    # time, max 1 order was opened)
                    log.warn(
                        "multiple orders were found according "
                        "to the trades: {} only the first is considered".format
                        ([x.id for x in missing_order_id_by_trade])
                    )
                order_id = missing_order_id_by_trade[0]
                return order_id, None

        return None, missing_order

    def _handle_request_timeout(self, dt_before, asset, amount, is_buy, style,
                                adj_amount):
        """
        Check if an order was received during the timeout, if it appeared
        on the orders dict return it to the user.
        If an order_id was traced alone, an order is created manually
        and returned to the user. Otherwise, send none to raise an
        error and retry the call.
        :param dt_before: pd.Timestamp
        :param asset: Asset
        :param amount: float
        :param is_buy: Bool
        :param style:
        :param adj_amount: int
        :return: missing_order: Order/ None
        """
        missing_order_id, missing_order = self._fetch_missing_order(
            dt_before=dt_before, symbol=asset.asset_name)

        if missing_order_id:
            final_amount = adj_amount if amount > 0 else -adj_amount
            missing_order = Order(
                dt=dt_before,
                asset=asset,
                amount=final_amount,
                stop=style.get_stop_price(is_buy),
                limit=style.get_limit_price(is_buy),
                id=missing_order_id
            )
        return missing_order

    def create_order(self, asset, amount, is_buy, style):
        symbol = self.get_symbol(asset)

        if isinstance(style, ExchangeLimitOrder):
            price = style.get_limit_price(is_buy)
            order_type = 'limit'

        elif isinstance(style, MarketOrder):
            price = None
            order_type = 'market'

        else:
            raise InvalidOrderStyle(
                exchange=self.name,
                style=style.__class__.__name__
            )

        side = 'buy' if amount > 0 else 'sell'
        if hasattr(self.api, 'amount_to_lots'):
            # TODO: is this right?
            if self.api.markets is None:
                self.api.load_markets()

            # https://github.com/ccxt/ccxt/issues/1483
            adj_amount = round(abs(amount), asset.decimals)
            market = self.api.markets[symbol]
            if 'lots' in market and market['lots'] > amount:
                raise CreateOrderError(
                    exchange=self.name,
                    e='order amount lower than the smallest lot: {}'.format(
                        amount
                    )
                )

        else:
            adj_amount = round(abs(amount), asset.decimals)

        before_order_dt = pd.Timestamp.utcnow()
        try:
            result = self.api.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=adj_amount,
                price=price
            )
        except InvalidOrder as e:
            log.warn('the exchange rejected the order: {}'.format(e))
            raise CreateOrderError(exchange=self.name, error=e)

        except RequestTimeout as e:
            log.info(
                'received a RequestTimeout exception while creating '
                'an order on {} / {}\n Checking if an order was filled '
                'during the timeout'.format(self.name, symbol)
            )

            missing_order = self._handle_request_timeout(
                before_order_dt, asset, amount, is_buy, style, adj_amount
            )
            if missing_order is None:
                # no order was found
                log.warn(
                    'no order was identified during timeout exception.'
                    'Please double check for inconsistency with the exchange. '
                    'We encourage you to report any issue on GitHub: '
                    'https://github.com/enigmampc/catalyst/issues'
                )
                raise ExchangeRequestError(error=e)
            else:
                return missing_order

        except (ExchangeError, NetworkError) as e:
            log.warn(
                'unable to create order {} / {}: {}'.format(
                    self.name, symbol, e
                )
            )
            raise ExchangeRequestError(error=e)

        exchange_amount = None
        if 'amount' in result and result['amount'] != adj_amount:
            exchange_amount = result['amount']

        elif 'info' in result:
            if 'origQty' in result['info']:
                exchange_amount = float(result['info']['origQty'])

        if exchange_amount:
            log.info(
                'order amount adjusted by {} from {} to {}'.format(
                    self.name, adj_amount, exchange_amount
                )
            )
            adj_amount = exchange_amount

        if 'info' not in result:
            raise ValueError('cannot use order without info attribute')

        final_amount = adj_amount if side == 'buy' else -adj_amount
        order_id = result['id']
        order = Order(
            dt=pd.Timestamp.utcnow(),
            asset=asset,
            amount=final_amount,
            stop=style.get_stop_price(is_buy),
            limit=style.get_limit_price(is_buy),
            id=order_id
        )
        return order

    def get_open_orders(self, asset):
        try:
            symbol = self.get_symbol(asset)
            result = self.api.fetch_open_orders(
                symbol=symbol,
                since=None,
                limit=None,
                params=dict()
            )
        except (ExchangeError, NetworkError) as e:
            log.warn(
                'unable to fetch open orders {} / {}: {}'.format(
                    self.name, asset.symbol, e
                )
            )
            raise ExchangeRequestError(error=e)

        orders = []
        for order_status in result:
            order, _ = self._create_order(order_status)
            if asset is None or asset == order.sid:
                orders.append(order)

        return orders

    def _check_common_symbols(self, currency):
        for key, value in self._common_symbols.items():
            if value == currency:
                return key.lower()
        return currency

    def _check_low_balance(self, currency, balances, amount):
        updated_currency = self._check_common_symbols(currency)
        return super(CCXT, self)._check_low_balance(updated_currency, balances,
                                                    amount)

    def _check_position_balance(self, currency, balances, amount):
        updated_currency = self._check_common_symbols(currency)
        return super(CCXT, self)._check_position_balance(updated_currency,
                                                         balances, amount)

    def _process_order_fallback(self, order):
        """
        Fallback method for exchanges which do not play nice with
        fetch-my-trades. Apparently, about 60% of exchanges will return
        the correct executed values with this method. Others will support
        fetch-my-trades.

        Parameters
        ----------
        order: Order

        Returns
        -------
        float

        """
        exc_order, price = self.get_order(
            order.id, order.asset, return_price=True
        )
        order.status = exc_order.status
        order.commission = exc_order.commission
        order.filled = exc_order.amount

        transactions = []
        if exc_order.status == ORDER_STATUS.FILLED:
            if order.amount > exc_order.amount:
                log.warn(
                    'executed order amount {} differs '
                    'from original'.format(
                        exc_order.amount, order.amount
                    )
                )

            order.check_triggers(
                price=price,
                dt=exc_order.dt,
            )
            transaction = Transaction(
                asset=order.asset,
                amount=order.amount,
                dt=pd.Timestamp.utcnow(),
                price=price,
                order_id=order.id,
                commission=order.commission,
            )
            transactions.append(transaction)

        return transactions

    def process_order(self, order):
        # TODO: move to parent class after tracking features in the parent
        if not self.api.has['fetchMyTrades']:
            return self._process_order_fallback(order)

        try:
            all_trades = self.get_trades(order.asset)
        except RequestTimeout as e:
            raise ExchangeRequestError(error="Received timeout from exchange")
        except ExchangeRequestError as e:
            log.warn(
                'unable to fetch account trades, trying an alternate '
                'method to find executed order {} / {}: {}'.format(
                    order.id, order.asset.symbol, e
                )
            )
            return self._process_order_fallback(order)

        transactions = []
        trades = [t for t in all_trades if t['order'] == order.id]
        if not trades:
            log.debug(
                'order {} / {} not found in trades'.format(
                    order.id, order.asset.symbol
                )
            )
            return transactions

        trades.sort(key=lambda t: t['timestamp'], reverse=False)
        order.filled = 0
        order.commission = 0
        for trade in trades:
            # status property will update automatically
            filled = trade['amount'] * order.direction
            order.filled += filled

            order.check_triggers(
                price=trade['price'],
                dt=pd.to_datetime(trade['timestamp'], unit='ms', utc=True),
            )

            commission = 0
            if 'fee' in trade and 'cost' in trade['fee']:
                # If the exchange gives info of the fees- from ccxt
                commission = trade['fee']['cost']
                order.commission += commission

            if 'fee' in trade and 'currency' in trade['fee']:
                transaction = Transaction(
                    asset=order.asset,
                    amount=filled,
                    dt=pd.Timestamp.utcnow(),
                    price=trade['price'],
                    order_id=order.id,
                    commission=commission,
                    fee_currency=trade['fee']['currency'].lower(),
                    is_quote_live=(self.quote_currency ==
                                   trade['fee']['currency'].lower())
                )
            else:
                transaction = Transaction(
                    asset=order.asset,
                    amount=filled,
                    dt=pd.Timestamp.utcnow(),
                    price=trade['price'],
                    order_id=order.id,
                    commission=commission,
                )
            transactions.append(transaction)

        order.filled = round(order.filled, order.asset.decimals)
        order.broker_order_id = ', '.join([t['id'] for t in trades])
        return transactions

    def get_order(self, order_id, asset_or_symbol=None, return_price=False):
        if asset_or_symbol is None:
            log.debug(
                'order not found in memory, the request might fail '
                'on some exchanges.'
            )
        try:
            symbol = self.get_symbol(asset_or_symbol) \
                if asset_or_symbol is not None else None
            order_status = self.api.fetch_order(id=order_id, symbol=symbol)
            order, executed_price = self._create_order(order_status)

            if return_price:
                return order, executed_price

            else:
                return order

        except (ExchangeError, NetworkError) as e:
            log.warn(
                'unable to fetch order {} / {}: {}'.format(
                    self.name, order_id, e
                )
            )
            raise ExchangeRequestError(error=e)

    def cancel_order(self, order_param,
                     asset_or_symbol=None, params={}):
        order_id = order_param.id \
            if isinstance(order_param, Order) else order_param

        if asset_or_symbol is None:
            log.debug(
                'order not found in memory, cancelling order might fail '
                'on some exchanges.'
            )
        try:
            symbol = self.get_symbol(asset_or_symbol) \
                if asset_or_symbol is not None else None
            self.api.cancel_order(id=order_id,
                                  symbol=symbol, params=params)

        except (ExchangeError, NetworkError) as e:
            log.warn(
                'unable to cancel order {} / {}: {}'.format(
                    self.name, order_id, e
                )
            )
            raise ExchangeRequestError(error=e)

    def tickers(self, assets, on_ticker_error='raise'):
        """
        Retrieve current tick data for the given assets

        Parameters
        ----------
        assets: list[TradingPair]

        Returns
        -------
        list[dict[str, float]

        """
        if len(assets) == 1 or not self.api.has['fetchTickers']:
            try:
                results = dict()
                for asset in assets:
                    symbol = self.get_symbol(asset)
                    log.debug('fetching single ticker: {}'.format(symbol))
                    results[symbol] = self.api.fetch_ticker(symbol=symbol)

            except (ExchangeError, NetworkError,) as e:
                log.warn(
                    'unable to fetch ticker {} / {}: {}'.format(
                        self.name, symbol, e
                    )
                )
                raise ExchangeRequestError(error=e)

        elif len(assets) > 1:
            symbols = self.get_symbols(assets)
            try:
                log.debug('fetching multiple tickers: {}'.format(symbols))
                results = self.api.fetch_tickers(symbols=symbols)

            except (ExchangeError, NetworkError) as e:
                log.warn(
                    'unable to fetch tickers {} / {}: {}'.format(
                        self.name, symbols, e
                    )
                )
                raise ExchangeRequestError(error=e)
        else:
            raise ValueError('Cannot request tickers with not assets.')

        tickers = dict()
        for asset in assets:
            symbol = self.get_symbol(asset)
            if symbol not in results:
                msg = 'ticker not found {} / {}'.format(
                    self.name, symbol
                )
                log.warn(msg)
                if on_ticker_error == 'warn':
                    continue
                else:
                    raise ExchangeRequestError(error=msg)

            ticker = results[symbol]
            ticker['last_traded'] = from_ms_timestamp(ticker['timestamp'])

            if 'last_price' not in ticker:
                # TODO: any more exceptions?
                ticker['last_price'] = ticker['last']

            if 'baseVolume' in ticker and ticker['baseVolume'] is not None:
                # Using the volume represented in the base currency
                ticker['volume'] = ticker['baseVolume']

            elif 'info' in ticker and 'bidQty' in ticker['info'] \
                    and 'askQty' in ticker['info']:
                ticker['volume'] = float(ticker['info']['bidQty']) + \
                                   float(ticker['info']['askQty'])

            else:
                ticker['volume'] = 0

            tickers[asset] = ticker

        return tickers

    def get_account(self):
        return None

    def get_orderbook(self, asset, order_type='all', limit=None):
        ccxt_symbol = self.get_symbol(asset)

        params = dict()
        if limit is not None:
            params['depth'] = limit

        order_book = self.api.fetch_order_book(ccxt_symbol, params)

        order_types = ['bids', 'asks'] if order_type == 'all' else [order_type]
        result = dict(last_traded=from_ms_timestamp(order_book['timestamp']))
        for index, order_type in enumerate(order_types):
            if limit is not None and index > limit - 1:
                break

            result[order_type] = []
            for entry in order_book[order_type]:
                result[order_type].append(dict(
                    rate=float(entry[0]),
                    quantity=float(entry[1])
                ))

        return result

    def get_trades(self, asset, my_trades=True, start_dt=None, limit=100):
        if not my_trades:
            raise NotImplemented(
                'get_trades only supports "my trades"'
            )

        # TODO: is it possible to sort this? Limit is useless otherwise.
        ccxt_symbol = self.get_symbol(asset)
        try:
            trades = self.api.fetch_my_trades(
                symbol=ccxt_symbol,
                since=start_dt,
                limit=limit,
            )
        except RequestTimeout as e:
            log.warn(
                'unable to fetch trades {} / {}: {}'.format(
                    self.name, asset.symbol, e
                )
            )
            raise e
        except (ExchangeError, NetworkError) as e:
            log.warn(
                'unable to fetch trades {} / {}: {}'.format(
                    self.name, asset.symbol, e
                )
            )
            raise ExchangeRequestError(error=e)

        return trades
