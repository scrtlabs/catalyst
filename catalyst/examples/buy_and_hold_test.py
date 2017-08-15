# code
import os
import re
from catalyst.api import order, record, symbol
from catalyst.exchange.algorithm_exchange import ExchangeTradingAlgorithm
from datetime import timedelta
from catalyst.exchange.bitfinex import Bitfinex
import pandas as pd
from catalyst.api import (
    order_target_value,
    symbol,
    record,
    cancel_order,
    get_open_orders,
)
from catalyst.algorithm import TradingAlgorithm
from catalyst.data.bundles.core import load
from catalyst.data.data_portal import DataPortal
from catalyst.data.loader import load_crypto_market_data
from catalyst.finance.trading import TradingEnvironment
from catalyst.pipeline.data import USEquityPricing, CryptoPricing
from catalyst.pipeline.loaders import (
    USEquityPricingLoader,
    CryptoPricingLoader,
)
from catalyst.utils.calendars import get_calendar
from functools import partial

bitfinex = Bitfinex()


def initialize(context):
    context.ASSET_NAME = 'USDT_BTC'
    context.TARGET_HODL_RATIO = 0.8
    context.RESERVE_RATIO = 1.0 - context.TARGET_HODL_RATIO

    # For all trading pairs in the poloniex bundle, the default denomination
    # currently supported by Catalyst is 1/1000th of a full coin. Use this
    # constant to scale the price of up to that of a full coin if desired.
    context.TICK_SIZE = 1000.0

    context.is_buying = True
    context.asset = symbol(context.ASSET_NAME)

    context.i = 0
    pass


def handle_data(context, data):
    context.i += 1

    print 'i:', context.i

    starting_cash = context.portfolio.starting_cash
    target_hodl_value = context.TARGET_HODL_RATIO * starting_cash
    reserve_value = context.RESERVE_RATIO * starting_cash

    # Cancel any outstanding orders
    orders = get_open_orders(context.asset) or []
    for order in orders:
        cancel_order(order)

    # Stop buying after passing the reserve threshold
    cash = context.portfolio.cash
    if cash <= reserve_value:
        context.is_buying = False

    # Retrieve current asset price from pricing data
    price = data[context.asset].price

    # Check if still buying and could (approximately) afford another purchase
    if context.is_buying and cash > price:
        # Place order to make position in asset equal to target_hodl_value
        order_target_value(
            context.asset,
            target_hodl_value,
            limit_price=price * 1.1,
            stop_price=price * 0.9,
        )

    record(
        price=price,
        cash=cash,
        starting_cash=context.portfolio.starting_cash,
        leverage=context.account.leverage,
    )


b = 'poloniex'
bundle_data = load(
    b,
    os.environ,
    pd.Timestamp.utcnow() - timedelta(days=10),
)

prefix, connstr = re.split(
    r'sqlite:///',
    str(bundle_data.asset_finder.engine.url),
    maxsplit=1,
)
if prefix:
    raise ValueError(
        "invalid url %r, must begin with 'sqlite:///'" %
        str(bundle_data.asset_finder.engine.url),
    )

open_calendar = get_calendar('OPEN')

env = TradingEnvironment(
    load=partial(load_crypto_market_data, environ=os.environ),
    bm_symbol='USDT_BTC',
    trading_calendar=open_calendar,
    asset_db_path=connstr,
    environ=os.environ,
)

first_trading_day = pd.Timestamp.utcnow() - timedelta(days=10)

data = DataPortal(
    env.asset_finder,
    open_calendar,
    first_trading_day=first_trading_day,
    minute_reader=bundle_data.minute_bar_reader,
    five_minute_reader=bundle_data.five_minute_bar_reader,
    daily_reader=bundle_data.daily_bar_reader,
    adjustment_reader=bundle_data.adjustment_reader,
)

algo_obj = ExchangeTradingAlgorithm(
    initialize=initialize,
    handle_data=handle_data,
    start=first_trading_day,
    end=pd.Timestamp.utcnow() - timedelta(days=1),
    exchange=bitfinex,
)

perf_manual = algo_obj.run(data, overwrite_sim_params=False)
