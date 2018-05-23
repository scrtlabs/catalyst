# cython: embedsignature=True
#
# Copyright 2015 Quantopian, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Cythonized Asset object.
"""

import hashlib

cimport cython
from cpython.number cimport PyNumber_Index
from cpython.object cimport (
Py_EQ,
Py_NE,
Py_GE,
Py_LE,
Py_GT,
Py_LT,
)
from cpython cimport bool

import pandas as pd
from datetime import timedelta
import numpy as np
from numpy cimport int64_t
import warnings
cimport numpy as np

from catalyst.exchange.utils.exchange_utils import get_sid
from catalyst.utils.calendars import get_calendar
from catalyst.exchange.exchange_errors import InvalidSymbolError, SidHashError

# IMPORTANT NOTE: You must change this template if you change
# Asset.__reduce__, or else we'll attempt to unpickle an old version of this
# class
CACHE_FILE_TEMPLATE = '/tmp/.%s-%s.v7.cache'

cdef class Asset:
    cdef readonly int sid
    # Cached hash of self.sid
    cdef int sid_hash

    cdef readonly object symbol
    cdef readonly object asset_name

    cdef readonly object start_date
    cdef readonly object end_date
    cdef public object first_traded
    cdef readonly object auto_close_date

    cdef readonly object exchange
    cdef readonly object exchange_full
    cdef readonly object min_trade_size

    _kwargnames = frozenset({
        'sid',
        'symbol',
        'asset_name',
        'start_date',
        'end_date',
        'first_traded',
        'auto_close_date',
        'exchange',
        'exchange_full',
        'min_trade_size',
    })

    def __init__(self,
                 int sid,  # sid is required
                 object exchange,  # exchange is required
                 object symbol="",
                 object asset_name="",
                 object start_date=None,
                 object end_date=None,
                 object first_traded=None,
                 object auto_close_date=None,
                 object exchange_full=None,
                 object min_trade_size=None):

        self.sid = sid
        self.sid_hash = hash(sid)
        self.symbol = symbol
        self.asset_name = asset_name
        self.exchange = exchange
        self.exchange_full = (exchange_full if exchange_full is not None
                              else exchange)
        self.start_date = start_date
        self.end_date = end_date
        self.first_traded = first_traded
        self.auto_close_date = auto_close_date
        self.min_trade_size = min_trade_size

    def __int__(self):
        return self.sid

    def __index__(self):
        return self.sid

    def __hash__(self):
        return self.sid_hash

    def __richcmp__(x, y, int op):
        """
        Cython rich comparison method.  This is used in place of various
        equality checkers in pure python.
        """
        cdef int x_as_int, y_as_int

        try:
            x_as_int = PyNumber_Index(x)
        except (TypeError, OverflowError):
            return NotImplemented

        try:
            y_as_int = PyNumber_Index(y)
        except (TypeError, OverflowError):
            return NotImplemented

        compared = x_as_int - y_as_int

        # Handle == and != first because they're significantly more common
        # operations.
        if op == Py_EQ:
            return compared == 0
        elif op == Py_NE:
            return compared != 0
        elif op == Py_LT:
            return compared < 0
        elif op == Py_LE:
            return compared <= 0
        elif op == Py_GT:
            return compared > 0
        elif op == Py_GE:
            return compared >= 0
        else:
            raise AssertionError('%d is not an operator' % op)

    def __str__(self):
        if self.symbol:
            return '%s(%d [%s])' % (type(self).__name__, self.sid, self.symbol)
        else:
            return '%s(%d)' % (type(self).__name__, self.sid)

    def __repr__(self):
        attrs = ('symbol', 'asset_name', 'exchange',
                 'start_date', 'end_date', 'first_traded', 'auto_close_date',
                 'min_trade_size')
        tuples = ((attr, repr(getattr(self, attr, None)))
                  for attr in attrs)
        strings = ('%s=%s' % (t[0], t[1]) for t in tuples)
        params = ', '.join(strings)
        return 'Asset(%d, %s)' % (self.sid, params)

    cpdef __reduce__(self):
        """
        Function used by pickle to determine how to serialize/deserialize this
        class.  Should return a tuple whose first element is self.__class__,
        and whose second element is a tuple of all the attributes that should
        be serialized/deserialized during pickling.
        """
        return (self.__class__, (self.sid,
                                 self.exchange,
                                 self.symbol,
                                 self.asset_name,
                                 self.start_date,
                                 self.end_date,
                                 self.first_traded,
                                 self.auto_close_date,
                                 self.exchange_full,
                                 self.min_trade_size))

    cpdef to_dict(self):
        """
        Convert to a python dict.
        """
        return {
            'sid': self.sid,
            'symbol': self.symbol,
            'asset_name': self.asset_name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'first_traded': self.first_traded,
            'auto_close_date': self.auto_close_date,
            'exchange': self.exchange,
            'exchange_full': self.exchange_full,
            'min_trade_size': self.min_trade_size
        }

    @classmethod
    def from_dict(cls, dict_):
        """
        Build an Asset instance from a dict.
        """
        return cls(**dict_)

    def is_alive_for_session(self, session_label):
        """
        Returns whether the asset is alive at the given dt.

        Parameters
        ----------
        session_label: pd.Timestamp
            The desired session label to check. (midnight UTC)

        Returns
        -------
        boolean: whether the asset is alive at the given dt.
        """
        cdef int64_t ref_start
        cdef int64_t ref_end

        ref_start = self.start_date.value
        ref_end = self.end_date.value

        return ref_start <= session_label.value <= ref_end

    def is_exchange_open(self, dt_minute):
        """
        Parameters
        ----------
        dt_minute: pd.Timestamp (UTC, tz-aware)
            The minute to check.

        Returns
        -------
        boolean: whether the asset's exchange is open at the given minute.
        """
        calendar = get_calendar(self.exchange)
        return calendar.is_open_on_minute(dt_minute)

cdef class Equity(Asset):
    def __repr__(self):
        attrs = ('symbol', 'asset_name', 'exchange',
                 'start_date', 'end_date', 'first_traded', 'auto_close_date',
                 'exchange_full', 'min_trade_size')
        tuples = ((attr, repr(getattr(self, attr, None)))
                  for attr in attrs)
        strings = ('%s=%s' % (t[0], t[1]) for t in tuples)
        params = ', '.join(strings)
        return 'Equity(%d, %s)' % (self.sid, params)

    property security_start_date:
        """
        DEPRECATION: This property should be deprecated and is only present for
        backwards compatibility
        """
        def __get__(self):
            warnings.warn("The security_start_date property will soon be "
                          "retired. Please use the start_date property instead.",
                          DeprecationWarning)
            return self.start_date

    property security_end_date:
        """
        DEPRECATION: This property should be deprecated and is only present for
        backwards compatibility
        """
        def __get__(self):
            warnings.warn("The security_end_date property will soon be "
                          "retired. Please use the end_date property instead.",
                          DeprecationWarning)
            return self.end_date

    property security_name:
        """
        DEPRECATION: This property should be deprecated and is only present for
        backwards compatibility
        """
        def __get__(self):
            warnings.warn("The security_name property will soon be "
                          "retired. Please use the asset_name property instead.",
                          DeprecationWarning)
            return self.asset_name

cdef class Future(Asset):
    cdef readonly object root_symbol
    cdef readonly object notice_date
    cdef readonly object expiration_date
    cdef readonly object tick_size
    cdef readonly float multiplier

    _kwargnames = frozenset({
        'sid',
        'symbol',
        'root_symbol',
        'asset_name',
        'start_date',
        'end_date',
        'notice_date',
        'expiration_date',
        'auto_close_date',
        'first_traded',
        'exchange',
        'tick_size',
        'multiplier',
        'exchange_full',
    })

    def __init__(self,
                 int sid,  # sid is required
                 object exchange,  # exchange is required
                 object symbol="",
                 object root_symbol="",
                 object asset_name="",
                 object start_date=None,
                 object end_date=None,
                 object notice_date=None,
                 object expiration_date=None,
                 object auto_close_date=None,
                 object first_traded=None,
                 object tick_size="",
                 float multiplier=1.0,
                 object exchange_full=None):

        super().__init__(
            sid,
            exchange,
            symbol=symbol,
            asset_name=asset_name,
            start_date=start_date,
            end_date=end_date,
            first_traded=first_traded,
            auto_close_date=auto_close_date,
            exchange_full=exchange_full,
        )
        self.root_symbol = root_symbol
        self.notice_date = notice_date
        self.expiration_date = expiration_date
        self.tick_size = tick_size
        self.multiplier = multiplier

        if auto_close_date is None:
            if notice_date is None:
                self.auto_close_date = expiration_date
            elif expiration_date is None:
                self.auto_close_date = notice_date
            else:
                self.auto_close_date = min(notice_date, expiration_date)

    def __repr__(self):
        attrs = ('symbol', 'root_symbol', 'asset_name', 'exchange',
                 'start_date', 'end_date', 'first_traded', 'notice_date',
                 'expiration_date', 'auto_close_date', 'tick_size',
                 'multiplier', 'exchange_full')
        tuples = ((attr, repr(getattr(self, attr, None)))
                  for attr in attrs)
        strings = ('%s=%s' % (t[0], t[1]) for t in tuples)
        params = ', '.join(strings)
        return 'Future(%d, %s)' % (self.sid, params)

    cpdef __reduce__(self):
        """
        Function used by pickle to determine how to serialize/deserialize this
        class.  Should return a tuple whose first element is self.__class__,
        and whose second element is a tuple of all the attributes that should
        be serialized/deserialized during pickling.
        """
        return (self.__class__, (self.sid,
                                 self.exchange,
                                 self.symbol,
                                 self.root_symbol,
                                 self.asset_name,
                                 self.start_date,
                                 self.end_date,
                                 self.notice_date,
                                 self.expiration_date,
                                 self.auto_close_date,
                                 self.first_traded,
                                 self.tick_size,
                                 self.multiplier,
                                 self.exchange_full))

    cpdef to_dict(self):
        """
        Convert to a python dict.
        """
        super_dict = super(Future, self).to_dict()
        super_dict['root_symbol'] = self.root_symbol
        super_dict['notice_date'] = self.notice_date
        super_dict['expiration_date'] = self.expiration_date
        super_dict['tick_size'] = self.tick_size
        super_dict['multiplier'] = self.multiplier
        return super_dict

cdef class TradingPair(Asset):
    cdef readonly float leverage
    cdef readonly object quote_currency
    cdef readonly object base_currency
    cdef readonly object end_daily
    cdef readonly object end_minute
    cdef readonly object exchange_symbol
    cdef readonly float maker
    cdef readonly float taker
    cdef readonly int trading_state
    cdef readonly object data_source
    cdef readonly float max_trade_size
    cdef readonly float lot
    cdef readonly int decimals

    _kwargnames = frozenset({
        'sid',
        'symbol',
        'asset_name',
        'start_date',
        'end_date',
        'first_traded',
        'auto_close_date',
        'exchange',
        'exchange_full',
        'leverage',
        'quote_currency',
        'base_currency',
        'end_daily',
        'end_minute',
        'exchange_symbol',
        'min_trade_size',
        'max_trade_size',
        'lot',
        'maker',
        'taker',
        'trading_state',
        'data_source',
        'decimals'
    })
    def __init__(self,
                 object symbol,
                 object exchange,
                 object start_date=None,
                 object asset_name=None,
                 int sid=0,
                 float leverage=1.0,
                 object end_daily=None,
                 object end_minute=None,
                 object end_date=None,
                 object exchange_symbol=None,
                 object first_traded=None,
                 object auto_close_date=None,
                 object exchange_full=None,
                 float min_trade_size=0.0001,
                 float max_trade_size=1000000,
                 float maker=0.0015,
                 float taker=0.0025,
                 float lot=0,
                 int decimals = 8,
                 int trading_state=0,
                 object data_source='catalyst'):
        """
        Replicates the Asset constructor with some built-in conventions
        and adds properties for leverage and fees.

        Symbol
        ------
        Catalyst defines its own set of "universal" symbols to reference
        trading pairs across exchanges. This is required because exchanges
        are not adhering to a universal symbolism. For example, Bitfinex
        uses the BTC symbol for Bitcon while Kraken uses XBT. In addition,
        pairs are sometimes presented differently. For example, Bitfinex
        puts the base currency before the quote currency without a
        separator, Bittrex puts the quote currency first and uses a dash
        seperator.

        Here is the Catalyst convention: [Base Currency]_[Quote Currency]
        For example: btc_usd, eth_btc, neo_eth, ltc_eur.

        The symbol for each currency (e.g. btc, eth, ltc) is generally
        aligned with the Bittrex exchange.

        Sid
        ---
        The sid of each asset is calculated based on a numeric hash of the
        universal symbol. This simple approach avoids maintaining a mapping
        of sids.

        Leverage
        --------
        In contrast with equities, crypto exchanges generally assign
        leverage values to specific trading pairs. Pairs with the
        highest volume and market cap generally benefit from high leverage.
        New currencies from ICO generally cannot be leveraged.

        Leverage allows you to open a larger position with a smaller amount
        of funds. For example, if you open a $5,000 position in BTC/USD
        with 5:1 leverage, only one-fifth of this amount, or $1000, will be
        tied to the position from your balance. Your remaining balance will
        be available for opening more positions. If you open this same
        position with 2:1 leverage, $2,500 of your balance will be tied to
        the position. If you open with 1:1 leverage, $5,000 of your balance
        will be tied to the position.

        Fees
        ----
        Exchanges generally charge a taker (taking from the order book) or
        maker (adding to the order book) fee.

        :param symbol:
        :param exchange:
        :param start_date:
        :param asset_name:
        :param sid:
        :param leverage:
        :param end_daily
        :param end_minute
        :param end_date:
        :param exchange_symbol:
        :param first_traded:
        :param auto_close_date:
        :param exchange_full:
        :param min_trade_size:
        :param max_trade_size:
        :param maker:
        :param taker:
        :param data_source
        :param decimals
        :param lot
        """

        symbol = symbol.lower()
        try:
            self.base_currency, self.quote_currency = symbol.split('_')
        except Exception as e:
            raise InvalidSymbolError(symbol=symbol, error=e)

        if sid == 0 or sid is None:
            try:
                sid = get_sid(symbol)
            except Exception as e:
                raise SidHashError(symbol=symbol)

        if asset_name is None:
            asset_name = ' / '.join(symbol.split('_')).upper()

        if start_date is None:
            start_date = pd.to_datetime('2009-1-1', utc=True)

        if end_date is None:
            end_date = pd.Timestamp.utcnow() + timedelta(days=365)

        if lot == 0 and min_trade_size > 0:
            lot = min_trade_size

        super().__init__(
            sid,
            exchange,
            symbol=symbol,
            asset_name=asset_name,
            start_date=start_date,
            end_date=end_date,
            first_traded=first_traded,
            auto_close_date=auto_close_date,
            exchange_full=exchange_full,
            min_trade_size=min_trade_size,
        )

        self.maker = maker
        self.taker = taker
        self.leverage = leverage
        self.end_daily = end_daily
        self.end_minute = end_minute
        self.exchange_symbol = exchange_symbol
        self.trading_state = trading_state
        self.data_source = data_source
        self.max_trade_size = max_trade_size
        self.lot = lot
        self.decimals = decimals

    def __repr__(self):
        return 'Trading Pair {symbol}({sid}) Exchange: {exchange}, ' \
               'Introduced On: {start_date}, ' \
               'Base Currency: {base_currency}, ' \
               'Quote Currency: {quote_currency}, ' \
               'Exchange Leverage: {leverage}, ' \
               'Minimum Trade Size: {min_trade_size} ' \
               'Last daily ingestion: {end_daily} ' \
               'Last minutely ingestion: {end_minute}'.format(
            symbol=self.symbol,
            sid=self.sid,
            exchange=self.exchange,
            start_date=self.start_date,
            quote_currency=self.quote_currency,
            base_currency=self.base_currency,
            leverage=self.leverage,
            min_trade_size=self.min_trade_size,
            end_daily=self.end_daily,
            end_minute=self.end_minute
        )

    cpdef to_dict(self):
        """
        Convert to a python dict.
        """
        #TODO: missing fields
        super_dict = super(TradingPair, self).to_dict()
        super_dict['end_daily'] = self.end_daily
        super_dict['end_minute'] = self.end_minute
        super_dict['leverage'] = self.leverage
        super_dict['min_trade_size'] = self.min_trade_size
        return super_dict

    def is_exchange_open(self, dt_minute):
        """
        Parameters
        ----------
        dt_minute: pd.Timestamp (UTC, tz-aware)
            The minute to check.

        Returns
        -------
        boolean: whether the asset's exchange is open at the given minute.
        """
        #TODO: make more dymanic to catch holds
        return True

    cpdef __reduce__(self):
        """
        Function used by pickle to determine how to serialize/deserialize this
        class.  Should return a tuple whose first element is self.__class__,
        and whose second element is a tuple of all the attributes that should
        be serialized/deserialized during pickling.
        """
        # added arguments for catalyst
        return (self.__class__, (self.symbol,
                                 self.exchange,
                                 self.start_date,
                                 self.asset_name,
                                 self.sid,
                                 self.leverage,
                                 self.end_daily,
                                 self.end_minute,
                                 self.end_date,
                                 self.exchange_symbol,
                                 self.first_traded,
                                 self.auto_close_date,
                                 self.exchange_full,
                                 self.min_trade_size,
                                 self.max_trade_size,
                                 self.maker,
                                 self.taker,
                                 self.lot,
                                 self.decimals,
                                 self.trading_state,
                                 self.data_source))

def make_asset_array(int size, Asset asset):
    cdef np.ndarray out = np.empty([size], dtype=object)
    out.fill(asset)
    return out
