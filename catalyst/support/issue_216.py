# -*- coding: utf-8 -*-
# !/usr/bin/env python2

import sys
import os
import pandas as pd
import signal
# import talib

from logbook import Logger

from catalyst import run_algorithm
from catalyst.api import (
    symbol,
    record,
    order,
    order_target,
    order_target_percent,
    get_open_orders
)
from catalyst.finance import commission


# from base.telegrambot import TelegramBot


class GracefulKiller:
    # Source: https://stackoverflow.com/a/31464349
    def __init__(self, context):
        self.kill_now = False
        self.signal = 0
        self.context = context
        signal.signal(signal.SIGINT, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True
        self.signal = signum
        if hasattr(self.context,
                   'telegram_bot') and self.context.telegram_bot is not None:
            self.context.telegram_bot.updater.stop()
        sys.exit(0)

    def exit(self):
        return self.kill_now


class SimulationParameters:
    MODE = 'paper'
    CAPITAL_BASE = 1000
    """
    Capital base used on this simulation
    """

    DATA_FREQUECY = 'minute'

    EXCHANGE_NAME = 'bitfinex'
    # EXCHANGE_NAME = 'binance'
    """
    Exchange used on this simulation
    """

    DATA_DIR = '/home/av/Dropbox/simulations/data'
    ALGO_NAMESPACE = os.path.basename(__file__).split('.')[0]
    ALGO_NAMESPACE_IMAGE = '{}/{}/{}.png'.format(DATA_DIR, 'images',
                                                 ALGO_NAMESPACE)
    ALGO_NAMESPACE_RESULTS_TABLE = '{}/{}/{}.csv'.format(DATA_DIR, 'tables',
                                                         ALGO_NAMESPACE + '_results')
    ALGO_NAMESPACE_TRANSACTIONS_TABLE = '{}/{}/{}.csv'.format(DATA_DIR,
                                                              'tables',
                                                              ALGO_NAMESPACE + '_transactions')
    QUOTE_CURRENCY = 'usd'
    # QUOTE_CURRENCY = 'usdt'

    # SHORT PERIOD
    START_DATE = '2017-09-07'
    """
    Start date used on this simulation
    """
    END_DATE = '2017-12-12'
    """
    End date used on this simulation
    """

    SKIP_FIRST_CANDLES = 0

    # CANDLES_SAMPLE_RATE = 60
    # CANDLES_SAMPLE_RATE = 30
    CANDLES_SAMPLE_RATE = 1
    """
    Candle interval used on this simulation (in minutes)
    """

    # http://pandas.pydata.org/pandas-docs/stable/timeseries.html#offset-aliases
    # 30 minute interval ohlcv data (the standard data required for candlestick or
    # indicators/signals)
    # 30T means 30 minutes re-sampling of one minute data.
    # CANDLES_FREQUENCY = '60T'
    # CANDLES_FREQUENCY = '30T'
    CANDLES_FREQUENCY = '1T'
    CANDLES_BUFFER_SIZE = 48
    COIN_PAIR = 'btc_usd'
    # COIN_PAIR = 'btc_usdt'
    """
    Coin pair used on this simulation
    """

    # TRANSACTIONS
    COMMISSION_FEE = 0.0030
    BUY_MIN_AMOUNT = 5  # i.e: USD
    SELL_MIN_AMOUNT = 0.001  # i.e: USD
    BUY_SELL_PERCENTAGE = 1  # 0.50
    BUY_PERCENTAGE = BUY_SELL_PERCENTAGE
    SELL_PERCENTAGE = BUY_SELL_PERCENTAGE

    BASE_PRICE = 'close'
    """
    Base price used (close / Heiken Ashi)
    """


log = None
parameters = None


def print_facts(context):
    context.log.info("""
Index: {}
Date: {}
Candle:
O: {}
H: {}
L: {}
C: {}
V: {}
Metrics:
...
Portfolio:
Base price: {}
Base coin (coin2/usd): {}
Amount (coin1/btc): {}
""".format(
        # Facts
        context.i,
        context.curr_minute,
        context.candles_open[-1],
        context.candles_high[-1],
        context.candles_low[-1],
        context.candles_close[-1],
        context.candles_volume[-1],
        # Metrics
        # ...
        # Portfolio
        context.curr_base_price,
        context.portfolio.cash,
        context.portfolio.positions[context.coin_pair].amount,
    ))


def print_facts_telegram(context):
    price = context.curr_base_price
    amount = context.portfolio.positions[context.coin_pair].amount
    pnl = context.portfolio.pnl
    capital_used = context.portfolio.capital_used
    portfolio_value = context.portfolio.portfolio_value
    portfolio_returns = context.portfolio.returns
    starting_cash = context.portfolio.starting_cash
    cash = context.portfolio.cash

    msg = """
Status...
Price: {}
Starting cash: {}
Cash: {}
Capital used: {}
Amount: {}
Portfolio value: {}
Returns: {}
PnL: {}
    """.format(
        price,
        starting_cash,
        cash,
        capital_used,
        amount,
        portfolio_value,
        portfolio_returns,
        pnl,
    )
    if hasattr(context, 'telegram_bot') and context.telegram_bot is not None:
        context.telegram_bot.msg(msg)


def default_initialize(context):
    # FIXME: set_benchmark
    # set_benchmark(symbol(context.parameters.COIN_PAIR))

    context.coin_pair = symbol(context.parameters.COIN_PAIR)
    context.base_price = None
    context.current_day = None
    context.counter = -1
    context.i = 0

    context.candles_sample_rate = context.parameters.CANDLES_SAMPLE_RATE
    context.candles_frequency = context.parameters.CANDLES_FREQUENCY
    context.candles_buffer_size = context.parameters.CANDLES_BUFFER_SIZE
    context.set_commission(
        commission.PerShare(cost=context.parameters.COMMISSION_FEE))


def default_handle_data(context, data):
    context.curr_minute = data.current_dt
    context.counter += 1

    if context.candles_sample_rate == 1:
        context.i += 1
    elif context.counter % context.candles_sample_rate != 0:
        context.i += 1
        return

    if context.i < context.parameters.SKIP_FIRST_CANDLES:
        return

    context.candles_open = data.history(
        context.coin_pair,
        'open',
        bar_count=context.candles_buffer_size,
        frequency=context.candles_frequency)
    context.candles_high = data.history(
        context.coin_pair,
        'high',
        bar_count=context.candles_buffer_size,
        frequency=context.candles_frequency)
    context.candles_low = data.history(
        context.coin_pair,
        'low',
        bar_count=context.candles_buffer_size,
        frequency=context.candles_frequency)
    context.candles_close = data.history(
        context.coin_pair,
        'price',
        bar_count=context.candles_buffer_size,
        frequency=context.candles_frequency)
    context.candles_volume = data.history(
        context.coin_pair,
        'volume',
        bar_count=context.candles_buffer_size,
        frequency=context.candles_frequency)

    # FIXME: Here is the error!
    # The candles_close frame shows more or less always a value of 94, while
    # bitcoin price is very different from that
    print(context.candles_close)

    context.base_prices = context.candles_close
    cash = context.portfolio.cash
    amount = context.portfolio.positions[context.coin_pair].amount
    price = data.current(context.coin_pair, 'price')
    order_id = None
    context.last_base_price = context.base_prices[-2]
    context.curr_base_price = context.base_prices[-1]

    # TA calculations
    # ...

    # Sanity checks
    # assert cash >= 0
    if cash < 0:
        import ipdb;
        ipdb.set_trace()  # BREAKPOINT

    print_facts(context)
    print_facts_telegram(context)

    # Order management
    net_shares = 0
    if context.counter == 2:
        brute_shares = (cash / price) * context.parameters.BUY_PERCENTAGE
        share_commission_fee = brute_shares * context.parameters.COMMISSION_FEE
        net_shares = brute_shares - share_commission_fee
        buy_order_id = order(context.coin_pair, net_shares)

    if context.counter == 3:
        brute_shares = amount * context.parameters.SELL_PERCENTAGE
        share_commission_fee = brute_shares * context.parameters.COMMISSION_FEE
        net_shares = -(brute_shares - share_commission_fee)
        sell_order_id = order(context.coin_pair, net_shares)

    # Record
    record(
        price=price,
        foo='bar',
        # volume=current['volume'],
        # price_change=price_change,
        # Metrics
        cash=cash,
        # buy=context.buy,
        # sell=context.sell
    )


def default_analyze(context=None, perf=None):
    pass


def initialize(context):
    global log
    context.parameters = parameters
    context.log = Logger(context.parameters.ALGO_NAMESPACE)
    log = context.log
    default_initialize(context)
    context.killer = GracefulKiller(context)
    context.telegram_bot = None

    # TELEGRAM_TOKEN='token'
    # context.telegram_bot = TelegramBot()
    # context.telegram_bot.initialize(TELEGRAM_TOKEN, context)


if __name__ == '__main__':
    # Parameters:
    parameters = SimulationParameters()
    start_date = pd.to_datetime(parameters.START_DATE, utc=True)
    end_date = pd.to_datetime(parameters.END_DATE, utc=True)

    if parameters.MODE == 'backtest':
        results = run_algorithm(
            capital_base=parameters.CAPITAL_BASE,
            data_frequency=parameters.DATA_FREQUECY,
            initialize=initialize,
            handle_data=default_handle_data,
            analyze=default_analyze,
            exchange_name=parameters.EXCHANGE_NAME,
            algo_namespace=parameters.ALGO_NAMESPACE,
            quote_currency=parameters.QUOTE_CURRENCY,
            start=start_date,
            end=end_date,
            live=False,
            live_graph=False
        )

        returns_daily = results
        results.to_csv('{}'.format(parameters.ALGO_NAMESPACE_RESULTS_TABLE))

        # returns_daily = returns_minutely.add(1).groupby(pd.TimeGrouper('24H')).prod().add(-1)

        # FIXME: pyfolio integration
        # pf_data = pyfolio.utils.extract_rets_pos_txn_from_zipline(results)
        # pf_data = pyfolio.utils.extract_rets_pos_txn_from_zipline(results[:'2017-01-01'])
        # pyfolio.create_full_tear_sheet(*pf_data)

    elif parameters.MODE == 'paper':
        results = run_algorithm(
            capital_base=parameters.CAPITAL_BASE,
            data_frequency=parameters.DATA_FREQUECY,
            initialize=initialize,
            handle_data=default_handle_data,
            analyze=default_analyze,
            exchange_name=parameters.EXCHANGE_NAME,
            algo_namespace=parameters.ALGO_NAMESPACE,
            quote_currency=parameters.QUOTE_CURRENCY,
            live=True,
            simulate_orders=True,
            live_graph=False
        )

    elif parameters.MODE == 'live':
        results = run_algorithm(
            initialize=initialize,
            handle_data=default_handle_data,
            analyze=default_analyze,
            exchange_name=parameters.EXCHANGE_NAME,
            algo_namespace=parameters.ALGO_NAMESPACE,
            quote_currency=parameters.QUOTE_CURRENCY,
            live=True,
            live_graph=True
        )
