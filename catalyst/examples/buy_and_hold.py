#!/usr/bin/env python
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

import numpy as np

from catalyst.api import (
    order,
    symbol,
    record,
)

TARGET_INVESTMENT_RATIO = 0.8

def initialize(context):
    context.has_ordered = False
    context.asset = symbol('USDT_ETH')


def handle_data(context, data):
    if not context.has_ordered:
        price = data[context.asset].price
        amt = TARGET_INVESTMENT_RATIO * (context.portfolio.cash / price)
        if not np.isnan(amt):
            print 'amt:', amt
            order(context.asset, amt, limit_price=price*1.5)
            context.has_ordered = True

    record(
        USDT_ETH=data[context.asset].price,
        cash=context.portfolio.cash,
        leverage=context.account.leverage,
    )

def analyze(context=None, results=None):
    import matplotlib.pyplot as plt
    # Plot the portfolio and asset data.
    ax1 = plt.subplot(511)
    results[['portfolio_value']].plot(ax=ax1)
    ax1.set_ylabel('Portfolio value (USD)')

    ax2 = plt.subplot(512, sharex=ax1)
    ax2.set_ylabel('USDT_ETH (USD)')
    results[['USDT_ETH']].plot(ax=ax2)

    trans = results.ix[[t != [] for t in results.transactions]]
    buys = trans.ix[
        [t[0]['amount'] > 0 for t in trans.transactions]
    ]
    sells = trans.ix[
        [t[0]['amount'] < 0 for t in trans.transactions]
    ]
    print 'buys:', buys.head()
    ax2.plot(
        buys.index, results.USDT_ETH[buys.index],
        '^',
        markersize=10,
        color='m',
    )
    ax2.plot(
        sells.index, results.USDT_ETH[sells.index],
        'v',
        markersize=10,
        color='k',
    )

    ax3 = plt.subplot(513, sharex=ax1)
    results[['leverage', 'alpha', 'beta']].plot(ax=ax3)
    ax3.set_ylabel('Leverage (USD)')

    ax4 = plt.subplot(514, sharex=ax1)
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

    ax5 = plt.subplot(515, sharex=ax1)
    results[[
        'treasury',
        'algorithm',
        'benchmark',
    ]].plot(ax=ax5)
    ax5.set_ylabel('Dollars (USD)')

    plt.legend(loc=3)

    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()


def _test_args():
    """Extra arguments to use when catalyst's automated tests run this example.
    """
    import pandas as pd

    return {
        'start': pd.Timestamp('2008', tz='utc'),
        'end': pd.Timestamp('2013', tz='utc'),
    }
