#!/usr/bin/env python
#
# Copyright 2017 Enigma MPC, Inc.
# Copyright 2014 Quantopian, Inc.
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

from catalyst.api import (
    order_target_percent,
    record,
    symbol,
    get_open_orders,
    set_max_leverage,
    schedule_function,
    date_rules,
    attach_pipeline,
    pipeline_output,
)

from catalyst.pipeline import Pipeline
from catalyst.pipeline.data import CryptoPricing
from catalyst.pipeline.factors.crypto import VWAP


def initialize(context):
    context.ASSET_NAME = 'USDT_BTC'
    context.TARGET_INVESTMENT_RATIO = 0.8
    context.SHORT_WINDOW = 30
    context.LONG_WINDOW = 100

    # For all trading pairs in the poloniex bundle, the default denomination
    # currently supported by Catalyst is 1/1000th of a full coin. Use this
    # constant to scale the price of up to that of a full coin if desired.
    context.TICK_SIZE = 1000.0

    context.i = 0
    context.asset = symbol(context.ASSET_NAME)

    set_max_leverage(1.0)

    attach_pipeline(make_pipeline(context), 'vwap_pipeline')

    schedule_function(
        rebalance,
        time_rules=times_rules.every_minute(),
    )


def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('vwap_pipeline')

def make_pipeline(context):
    return Pipeline(
        columns={
            'price': CryptoPricing.open.latest,
            'volume': CryptoPricing.volume.latest,
            'short_mavg': VWAP(window_length=context.SHORT_WINDOW),
            'long_mavg': VWAP(window_length=context.LONG_WINDOW),
        }
    )

def rebalance(context, data):
    context.i += 1

    # skip first LONG_WINDOW bars to fill windows
    if context.i < context.LONG_WINDOW:
        return

    # get pipeline data for asset of interest
    pipeline_data = context.pipeline_data
    pipeline_data = pipeline_data[pipeline_data.index == context.asset].iloc[0]

    # retrieve long and short moving averages from pipeline
    short_mavg = pipeline_data.short_mavg
    long_mavg = pipeline_data.long_mavg
    price = pipeline_data.price
    volume = pipeline_data.volume

    # check that order has not already been placed
    open_orders = get_open_orders()
    if context.asset not in open_orders:
        # check that the asset of interest can currently be traded
        if data.can_trade(context.asset):
            # adjust portfolio based on comparison of long and short vwap
            if short_mavg > long_mavg:
                order_target_percent(
                    context.asset,
                    context.TARGET_INVESTMENT_RATIO,
                )
            elif short_mavg < long_mavg:
                order_target_percent(
                    context.asset,
                    0.0,
                )

    record(
        price=price,
        cash=context.portfolio.cash,
        leverage=context.account.leverage,
        short_mavg=short_mavg,
        long_mavg=long_mavg,
        volume=volume,
    )
    


def analyze(context=None, results=None):
    import matplotlib.pyplot as plt

    # Plot the portfolio and asset data.
    ax1 = plt.subplot(611)
    results[['portfolio_value']].plot(ax=ax1)
    ax1.set_ylabel('Portfolio value (USD)')

    ax2 = plt.subplot(612, sharex=ax1)
    ax2.set_ylabel('{asset} (USD)'.format(asset=context.ASSET_NAME))
    (context.TICK_SIZE*results[['price', 'short_mavg', 'long_mavg']]).plot(ax=ax2)

    trans = results.ix[[t != [] for t in results.transactions]]
    amounts = [t[0]['amount'] for t in trans.transactions]

    buys = trans.ix[
        [t[0]['amount'] > 0 for t in trans.transactions]
    ]
    sells = trans.ix[
        [t[0]['amount'] < 0 for t in trans.transactions]
    ]

    ax2.plot(
        buys.index,
        context.TICK_SIZE * results.price[buys.index],
        '^',
        markersize=10,
        color='g',
    )
    ax2.plot(
        sells.index,
        context.TICK_SIZE * results.price[sells.index],
        'v',
        markersize=10,
        color='r',
    )

    ax3 = plt.subplot(613, sharex=ax1)
    results[['leverage', 'alpha', 'beta']].plot(ax=ax3)
    ax3.set_ylabel('Leverage (USD)')

    ax4 = plt.subplot(614, sharex=ax1)
    results[['cash']].plot(ax=ax4)
    ax4.set_ylabel('Cash (USD)')

    results[[
        'treasury',
        'algorithm',
        'benchmark',
    ]] = results[[
        'treasury_period_return',
        'algorithm_period_return',
        'benchmark_period_return',
    ]]

    ax5 = plt.subplot(615, sharex=ax1)
    results[[
        'treasury',
        'algorithm',
        'benchmark',
    ]].plot(ax=ax5)
    ax5.set_ylabel('Percent Change')

    ax6 = plt.subplot(616, sharex=ax1)
    results[['volume']].plot(ax=ax6)
    ax6.set_ylabel('Volume (mBTC/day)')

    plt.legend(loc=3)

    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()
