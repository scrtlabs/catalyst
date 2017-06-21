#!/usr/bin/env python
#
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
)


def initialize(context):
    context.asset = symbol('USDT_BTC')


def handle_data(context, data):
    if context.asset not in get_open_orders() and data.can_trade(context.asset):
        order_target_percent(context.asset, 1.0)

    record(
        USDT_BTC=data.current(context.asset, 'price'),
        leverage=context.account.leverage,
    )


# Note: this function can be removed if running
# this algorithm on quantopian.com
def analyze(context=None, results=None):
    import matplotlib.pyplot as plt
    # Plot the portfolio and asset data.
    ax1 = plt.subplot(311)
    results.portfolio_value.plot(ax=ax1)
    ax1.set_ylabel('Portfolio value (USD)')
    ax2 = plt.subplot(312, sharex=ax1)
    results.USDT_BTC.plot(ax=ax2)
    ax2.set_ylabel('USDT_BTC price (USD)')
    ax3 = plt.subplot(313, sharex=ax1)
    results.leverage.plot(ax=ax3)
    ax3.set_ylabel('Leverage (USD)')

    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()


def _test_args():
    """Extra arguments to use when catalyst's automated tests run this example.
    """
    import pandas as pd

    return {
        'start': pd.Timestamp('2014-01-01', tz='utc'),
        'end': pd.Timestamp('2014-11-01', tz='utc'),
    }
