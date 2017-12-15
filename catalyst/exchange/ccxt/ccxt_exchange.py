import json
import re
from collections import defaultdict

import ccxt
import os
import pandas as pd
import six
from ccxt import ExchangeNotAvailable, InvalidOrder
from logbook import Logger
from six import string_types

from catalyst.algorithm import MarketOrder
from catalyst.assets._assets import TradingPair
from catalyst.constants import LOG_LEVEL
from catalyst.exchange.exchange import Exchange
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.exchange_errors import InvalidHistoryFrequencyError, \
    ExchangeSymbolsNotFound, ExchangeRequestError, InvalidOrderStyle, \
    ExchangeNotFoundError, CreateOrderError, InvalidHistoryTimeframeError
from catalyst.exchange.exchange_execution import ExchangeLimitOrder
from catalyst.exchange.exchange_utils import mixin_market_params, \
    from_ms_timestamp, get_epoch, get_exchange_folder, get_catalyst_symbol
from catalyst.finance.order import Order, ORDER_STATUS

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
    def __init__(self, exchange_name, key, secret, base_currency):
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
            })

        except Exception:
            raise ExchangeNotFoundError(exchange_name=exchange_name)

        self._symbol_maps = [None, None]

        self.name = exchange_name

        self.base_currency = base_currency
        self.transactions = defaultdict(list)

        self.num_candles_limit = 2000
        self.max_requests_per_minute = 60
        self.request_cpt = dict()

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

            except ExchangeNotAvailable as e:
                raise ExchangeRequestError(error=e)

        self.load_assets()
        self._is_init = True

    @staticmethod
    def find_exchanges(features=None):
        exchange_names = []
        for exchange_name in ccxt.exchanges:
            log.debug('loading exchange: {}'.format(exchange_name))
            exchange = getattr(ccxt, exchange_name)()

            if features is None:
                has_feature = True

            else:
                try:
                    has_feature = all(
                        [exchange.has[feature] for feature in features]
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

    def get_candle_frequencies(self):
        frequencies = []
        try:
            for timeframe in self.api.timeframes:
                frequencies.append(
                    CCXT.get_frequency(timeframe, raise_error=False)
                )

        except Exception:
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

    def get_symbol(self, asset_or_symbol):
        """
        The CCXT symbol.

        Parameters
        ----------
        asset_or_symbol

        Returns
        -------

        """
        symbol = asset_or_symbol if isinstance(
            asset_or_symbol, string_types
        ) else asset_or_symbol.symbol

        parts = symbol.split('_')
        return '{}/{}'.format(parts[0].upper(), parts[1].upper())

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
        freq_match = re.match(r'([0-9].*)?(m|M|d|D|h|H|T)', freq, re.M | re.I)
        if freq_match:
            candle_size = int(freq_match.group(1)) \
                if freq_match.group(1) else 1

            unit = freq_match.group(2)

        else:
            raise InvalidHistoryFrequencyError(frequency=freq)

        if unit.lower() == 'd':
            timeframe = '{}d'.format(candle_size)

        elif unit.lower() == 'm' or unit == 'T':
            timeframe = '{}m'.format(candle_size)

        elif unit.lower() == 'h' or unit == 'T':
            timeframe = '{}h'.format(candle_size)

        elif raise_error:
            raise InvalidHistoryFrequencyError(frequency=freq)

        return timeframe

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
        timeframe_match = re.match(
            r'([0-9].*)?(m|M|d|h|w|y)', timeframe, re.M | re.I
        )
        if timeframe_match:
            candle_size = int(timeframe_match.group(1)) \
                if timeframe_match.group(1) else 1

            unit = timeframe_match.group(2)

        else:
            raise InvalidHistoryTimeframeError(timeframe=timeframe)

        if unit.lower() == 'd':
            freq = '{}D'.format(candle_size)

        elif unit.lower() == 'm':
            freq = '{}T'.format(candle_size)

        elif unit.lower() == 'h':
            freq = '{}H'.format(candle_size)

        elif unit.lower() == 'w':
            freq = '{}D'.format(candle_size * 7)

        elif raise_error:
            raise InvalidHistoryTimeframeError(timeframe=timeframe)

        return freq

    def get_candles(self, freq, assets, bar_count=None, start_dt=None,
                    end_dt=None):
        is_single = (isinstance(assets, TradingPair))
        if is_single:
            assets = [assets]

        symbols = self.get_symbols(assets)
        timeframe = CCXT.get_timeframe(freq)

        ms = None
        if start_dt is not None:
            delta = start_dt - get_epoch()
            ms = int(delta.total_seconds()) * 1000

        candles = dict()
        for asset in assets:
            try:
                ohlcvs = self.api.fetch_ohlcv(
                    symbol=symbols[0],
                    timeframe=timeframe,
                    since=ms,
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

            except Exception as e:
                raise ExchangeRequestError(error=e)

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

        except Exception as e:
            log.debug('error retrieving balances: {}', e)
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
        if order_status['status'] == 'canceled':
            status = ORDER_STATUS.CANCELLED

        elif order_status['status'] == 'closed' and order_status['filled'] > 0:
            log.debug('found executed order {}'.format(order_status))
            status = ORDER_STATUS.FILLED

        elif order_status['status'] == 'open':
            status = ORDER_STATUS.OPEN

        else:
            log.warn(
                'invalid state {} for order {}'.format(
                    order_status['status'], order_status['id']
                )
            )
            status = ORDER_STATUS.OPEN

        amount = order_status['amount']
        filled = order_status['filled']

        if order_status['side'] == 'sell':
            amount = -amount
            filled = -filled

        price = order_status['price']
        order_type = order_status['type']

        limit_price = price if order_type == 'limit' else None
        stop_price = None  # TODO: add support

        executed_price = order_status['cost'] / order_status['amount']
        commission = order_status['fee']
        date = from_ms_timestamp(order_status['timestamp'])

        # order_id = str(order_status['info']['clientOrderId'])
        order_id = order_status['id']

        # TODO: this won't work, redo the packages with a different key.
        symbol = order_status['info']['symbol'] \
            if 'symbol' in order_status['info'] \
            else order_status['info']['Exchange']

        order = Order(
            dt=date,
            asset=self.get_asset(symbol, is_exchange_symbol=True),
            amount=amount,
            stop=stop_price,
            limit=limit_price,
            filled=filled,
            id=order_id,
            commission=commission
        )
        order.status = status

        return order, executed_price

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
            adj_amount = self.api.amount_to_lots(
                symbol=symbol,
                amount=abs(amount),
            )
            if adj_amount != abs(amount):
                log.info(
                    'adjusted order amount {} to {} based on lot size'.format(
                        abs(amount), adj_amount,
                    )
                )
        else:
            adj_amount = abs(amount)

        try:
            result = self.api.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=adj_amount,
                price=price
            )
        except ExchangeNotAvailable as e:
            log.debug('unable to create order: {}'.format(e))
            raise ExchangeRequestError(error=e)

        except InvalidOrder as e:
            log.warn('the exchange rejected the order: {}'.format(e))
            raise CreateOrderError(exchange=self.name, error=e)

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
        except Exception as e:
            raise ExchangeRequestError(error=e)

        orders = []
        for order_status in result:
            order, executed_price = self._create_order(order_status)
            if asset is None or asset == order.sid:
                orders.append(order)

        return orders

    def get_order(self, order_id, asset_or_symbol=None):
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

        except Exception as e:
            raise ExchangeRequestError(error=e)

        return order, executed_price

    def cancel_order(self, order_param, asset_or_symbol=None):
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
            self.api.cancel_order(id=order_id, symbol=symbol)

        except Exception as e:
            raise ExchangeRequestError(error=e)

    def tickers(self, assets):
        """
        Retrieve current tick data for the given assets

        Parameters
        ----------
        assets: list[TradingPair]

        Returns
        -------
        list[dict[str, float]

        """
        tickers = dict()
        try:
            symbols = [self.get_symbol(asset) for asset in assets]
            ccxt_tickers = self.api.fetch_tickers(symbols)

            for asset in assets:
                symbol = self.get_symbol(asset)
                if symbol not in ccxt_tickers:
                    log.warn('ticker not found for {} {}'.format(
                        self.name, symbol
                    ))
                    continue

                ticker = ccxt_tickers[symbol]
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

        except ExchangeNotAvailable as e:
            log.warn(
                'unable to fetch ticker: {} {}'.format(
                    self.name, asset.symbol
                )
            )
            raise ExchangeRequestError(error=e)

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
