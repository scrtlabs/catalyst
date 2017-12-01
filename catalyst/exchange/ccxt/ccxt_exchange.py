import re
from collections import defaultdict

import ccxt
import pandas as pd
from ccxt import ExchangeNotAvailable
from six import string_types

from catalyst.finance.order import Order, ORDER_STATUS

from catalyst.algorithm import MarketOrder
from catalyst.assets._assets import TradingPair
from logbook import Logger

from catalyst.constants import LOG_LEVEL
from catalyst.exchange.exchange import Exchange, ExchangeLimitOrder
from catalyst.exchange.exchange_bundle import ExchangeBundle
from catalyst.exchange.exchange_errors import InvalidHistoryFrequencyError, \
    ExchangeSymbolsNotFound, ExchangeRequestError, InvalidOrderStyle, \
    ExchangeNotFoundError
from catalyst.exchange.exchange_utils import mixin_market_params, \
    from_ms_timestamp

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
    def __init__(self, exchange_name, key, secret, base_currency,
                 portfolio=None):
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

        markets = self.api.load_markets()
        log.debug('the markets:\n{}'.format(markets))

        self.name = exchange_name

        self.assets = dict()
        self.load_assets()

        self.base_currency = base_currency
        self._portfolio = portfolio
        self.transactions = defaultdict(list)

        self.num_candles_limit = 2000
        self.max_requests_per_minute = 60
        self.request_cpt = dict()

        self.bundle = ExchangeBundle(self.name)

    def account(self):
        return None

    def time_skew(self):
        return None

    def get_symbol(self, asset_or_symbol):
        symbol = asset_or_symbol if isinstance(
            asset_or_symbol, string_types
        ) else asset_or_symbol.symbol

        parts = symbol.split('_')
        return '{}/{}'.format(parts[0].upper(), parts[1].upper())

    def get_catalyst_symbol(self, market_or_symbol):
        if isinstance(market_or_symbol, string_types):
            parts = market_or_symbol.split('/')
            return '{}_{}'.format(parts[0].lower(), parts[1].lower())

        else:
            return '{}_{}'.format(
                market_or_symbol['base'].lower(),
                market_or_symbol['quote'].lower(),
            )

    def get_timeframe(self, freq):
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

        return timeframe

    def get_candles(self, freq, assets, bar_count=None, start_dt=None,
                    end_dt=None):
        symbols = self.get_symbols(assets)
        timeframe = self.get_timeframe(freq)
        delta = start_dt - pd.to_datetime('1970-1-1', utc=True)
        ms = int(delta.total_seconds()) * 1000

        candles = dict()
        for asset in assets:
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
                    last_traded=pd.to_datetime(ohlcv[0], unit='ms', utc=True),
                    open=ohlcv[1],
                    high=ohlcv[2],
                    low=ohlcv[3],
                    close=ohlcv[4],
                    volume=ohlcv[5]
                ))

        return candles

    def _fetch_symbol_map(self, is_local):
        try:
            return self.fetch_symbol_map(is_local)
        except ExchangeSymbolsNotFound:
            return None

    def _fetch_asset(self, market_id, is_local=False):
        symbol_map = self._fetch_symbol_map(is_local)
        if symbol_map is not None:
            assets_lower = {k.lower(): v for k, v in symbol_map.items()}
            key = market_id.lower()

            asset = assets_lower[key] if key in assets_lower else None
            if asset is not None:
                return asset, is_local

            elif not is_local:
                return self._fetch_asset(market_id, True)

            else:
                return None, is_local

        elif not is_local:
            return self._fetch_asset(market_id, True)

        else:
            return None, is_local

    def load_assets(self):
        markets = self.api.fetch_markets()

        for market in markets:
            asset, is_local = self._fetch_asset(market['id'])
            data_source = 'local' if is_local else 'catalyst'

            params = dict(
                exchange=self.name,
                data_source=data_source,
                exchange_symbol=market['id'],
            )
            mixin_market_params(self.name, params, market)

            if asset is not None:
                params['symbol'] = asset['symbol']

                params['start_date'] = pd.to_datetime(
                    asset['start_date'], utc=True
                ) if 'start_date' in asset else None

                params['end_date'] = pd.to_datetime(
                    asset['end_date'], utc=True
                ) if 'end_date' in asset else None

                params['leverage'] = asset['leverage'] \
                    if 'leverage' in asset else 1.0

                params['asset_name'] = asset['asset_name'] \
                    if 'asset_name' in asset else None

                params['end_daily'] = pd.to_datetime(
                    asset['end_daily'], utc=True
                ) if 'end_daily' in asset and asset['end_daily'] != 'N/A' \
                    else None

                params['end_minute'] = pd.to_datetime(
                    asset['end_minute'], utc=True
                ) if 'end_minute' in asset and asset['end_minute'] != 'N/A' \
                    else None

            else:
                params['symbol'] = self.get_catalyst_symbol(market)

            trading_pair = TradingPair(**params)
            self.assets[market['id']] = trading_pair

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
            raise ValueError('invalid state for order')

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
        symbol = order_status['info']['symbol']

        order = Order(
            dt=date,
            asset=self.assets[symbol],
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

        try:
            result = self.api.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=abs(amount),
                price=price
            )
        except ExchangeNotAvailable as e:
            log.debug('unable to create order: {}'.format(e))
            raise ExchangeRequestError(error=e)

        if 'info' not in result:
            raise ValueError('cannot use order without info attribute')

        # order_id = str(result['info']['clientOrderId'])
        order_id = result['id']
        order = Order(
            dt=from_ms_timestamp(result['info']['transactTime']),
            asset=asset,
            amount=amount,
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

    def _get_asset_from_order(self, order_id):
        open_orders = self.portfolio.open_orders
        order = next(
            (order for order in open_orders if order.id == order_id),
            None
        )  # type: Order
        return order.asset if order is not None else None

    def get_order(self, order_id, asset_or_symbol=None):
        if asset_or_symbol is None and self.portfolio is not None:
            asset_or_symbol = self._get_asset_from_order(order_id)

        if asset_or_symbol is None:
            log.debug(
                'order not found in memory, the request might fail '
                'on some exchanges.'
            )
        try:
            symbol = self.get_symbol(asset_or_symbol) \
                if asset_or_symbol is not None else None
            order_status = self.api.fetch_order(id=order_id, symbol=symbol)
            order, _ = self._create_order(order_status)

        except Exception as e:
            raise ExchangeRequestError(error=e)

        return order

    def cancel_order(self, order_param, asset_or_symbol=None):
        order_id = order_param.id \
            if isinstance(order_param, Order) else order_param

        if asset_or_symbol is None and self.portfolio is not None:
            asset_or_symbol = self._get_asset_from_order(order_id)

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
        for asset in assets:
            ccxt_symbol = self.get_symbol(asset)
            ticker = self.api.fetch_ticker(ccxt_symbol)

            ticker['last_traded'] = from_ms_timestamp(ticker['timestamp'])

            # Using the volume represented in the base currency
            ticker['volume'] = ticker['baseVolume'] \
                if 'baseVolume' in ticker else 0

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
