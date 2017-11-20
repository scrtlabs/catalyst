|
Example Algorithms
==================

This section documents a small number of example algorithms to complement the 
beginner tutorial, and show how other trading algorithms can be implemented 
using Catalyst:

.. _buy_and_hodl:

Buy and Hodl Algorithm
~~~~~~~~~~~~~~~~~~~~~~

source: `examples/buy_and_hodl.py <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/buy_and_hodl.py>`_

First ingest the historical pricing data needed to run this algorithm:

.. code-block:: bash

   catalyst ingest-exchange -x poloniex -f daily -i btc_usdt

Then, you can run the code below with the following command:

.. code-block:: bash

   catalyst run -f buy_and_hodl.py --start 2015-3-1 --end 2017-10-31 --capital-base 100000 -x poloniex -c btc -o bah.pickle

This command will run the trading algorithm in the specified time range and 
plot the resulting performance using the matplotlib library. You can choose any 
date interval with the ``--start`` and ``--end`` parameters, but bear in mind 
that 2015-3-1 is the earliest date that Catalyst supports (if you choose an 
earlier date, you'll get an error), and the most recent date you can choose is 
one day prior to the current date. 


.. code-block:: python

   #!/usr/bin/env python
   #
   # Copyright 2017 Enigma MPC, Inc.
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
   import pandas as pd

   from catalyst.api import (
       order_target_value,
       symbol,
       record,
       cancel_order,
       get_open_orders,
   )


   def initialize(context):
       context.ASSET_NAME = 'btc_usdt'
       context.TARGET_HODL_RATIO = 0.8
       context.RESERVE_RATIO = 1.0 - context.TARGET_HODL_RATIO

       context.is_buying = True
       context.asset = symbol(context.ASSET_NAME)

       context.i = 0


   def handle_data(context, data):
       context.i += 1

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
       price = data.current(context.asset, 'price')

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
           volume=data.current(context.asset, 'volume'),
           cash=cash,
           starting_cash=context.portfolio.starting_cash,
           leverage=context.account.leverage,
       )


   def analyze(context=None, results=None):
       import matplotlib.pyplot as plt

       # Plot the portfolio and asset data.
       ax1 = plt.subplot(611)
       results[['portfolio_value']].plot(ax=ax1)
       ax1.set_ylabel('Portfolio Value (USD)')

       ax2 = plt.subplot(612, sharex=ax1)
       ax2.set_ylabel('{asset} (USD)'.format(asset=context.ASSET_NAME))
       results[['price']].plot(ax=ax2)

       trans = results.ix[[t != [] for t in results.transactions]]
       buys = trans.ix[
           [t[0]['amount'] > 0 for t in trans.transactions]
       ]
       ax2.plot(
           buys.index,
           results.price[buys.index],
           '^',
           markersize=10,
           color='g',
       )

       ax3 = plt.subplot(613, sharex=ax1)
       results[['leverage', 'alpha', 'beta']].plot(ax=ax3)
       ax3.set_ylabel('Leverage ')

       ax4 = plt.subplot(614, sharex=ax1)
       results[['starting_cash', 'cash']].plot(ax=ax4)
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
       ax6.set_ylabel('Volume (mCoins/5min)')

       plt.legend(loc=3)

       # Show the plot.
       plt.gcf().set_size_inches(18, 8)
       plt.show()

.. _mean_reversion:

Mean Reversion Algorithm
~~~~~~~~~~~~~~~~~~~~~~~~

source: `examples/mean_reversion_simple.py <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/mean_reversion_simple.py>`_

This algorithm is based on a simple momentum strategy. When the cryptoasset goes
up quickly, we're going to buy; when it goes down quickly, we're going to sell. 
Hopefully, we'll ride the waves.

We are choosing to run this trading algorithm with the ``neo_usd`` currency pair
on the ``Bitfinex`` exchange. Thus, first ingest the historical pricing data
that we need, with minute resolution:

.. code-block:: bash

   catalyst ingest-exchange -x bitfinex -f minute -i neo_usd

To run this algorithm, we are opting for the Python interpreter, instead of the 
command line (CLI). All of the parameters for the simulation are specified in 
lines 218-245, so in order to run the algorithm we just type:

.. code-block:: bash

   python mean_reversion_simple.py

.. code-block:: python

   import pandas as pd
   import talib
   from logbook import Logger

   from catalyst import run_algorithm
   from catalyst.api import symbol, record, order_target_percent, get_open_orders
   from catalyst.exchange.stats_utils import extract_transactions

   # We give a name to the algorithm which Catalyst will use to persist its state.
   # In this example, Catalyst will create the `.catalyst/data/live_algos`
   # directory. If we stop and start the algorithm, Catalyst will resume its
   # state using the files included in the folder.
   NAMESPACE = 'mean_reversion_simple'
   log = Logger(NAMESPACE)

   # To run an algorithm in Catalyst, you need two functions: initialize and
   # handle_data.

   def initialize(context):
       # This initialize function sets any data or variables that you'll use in
       # your algorithm.  For instance, you'll want to define the trading pair (or
       # trading pairs) you want to backtest.  You'll also want to define any
       # parameters or values you're going to use.

       # In our example, we're looking at Ether in USD Tether.
       context.neo_usd = symbol('neo_usd')
       context.base_price = None
       context.current_day = None


   def handle_data(context, data):
       # This handle_data function is where the real work is done.  Our data is
       # minute-level tick data, and each minute is called a frame.  This function
       # runs on each frame of the data.

       # We flag the first period of each day.
       # Since cryptocurrencies trade 24/7 the `before_trading_starts` handle
       # would only execute once. This method works with minute and daily
       # frequencies.
       today = data.current_dt.floor('1D')
       if today != context.current_day:
           context.traded_today = False
           context.current_day = today

       # We're computing the volume-weighted-average-price of the security
       # defined above, in the context.neo_usd variable.  For this example, we're 
       # using three bars on the 15 min bars.

       # The frequency attribute determine the bar size. We use this convention
       # for the frequency alias:
       # http://pandas.pydata.org/pandas-docs/stable/timeseries.html#offset-aliases
       prices = data.history(
           context.neo_usd,
           fields='close',
           bar_count=50,
           frequency='15T'
       )

       # Ta-lib calculates various technical indicator based on price and
       # volume arrays.

       # In this example, we are comp
       rsi = talib.RSI(prices.values, timeperiod=14)

       # We need a variable for the current price of the security to compare to
       # the average. Since we are requesting two fields, data.current()
       # returns a DataFrame with
       current = data.current(context.neo_usd, fields=['close', 'volume'])
       price = current['close']

       # If base_price is not set, we use the current value. This is the
       # price at the first bar which we reference to calculate price_change.
       if context.base_price is None:
           context.base_price = price

       price_change = (price - context.base_price) / context.base_price
       cash = context.portfolio.cash

       # Now that we've collected all current data for this frame, we use
       # the record() method to save it. This data will be available as
       # a parameter of the analyze() function for further analysis.
       record(
           price=price,
           volume=current['volume'],
           price_change=price_change,
           rsi=rsi[-1],
           cash=cash
       )

       # We are trying to avoid over-trading by limiting our trades to
       # one per day.
       if context.traded_today:
           return

       # Since we are using limit orders, some orders may not execute immediately
       # we wait until all orders are executed before considering more trades.
       orders = get_open_orders(context.neo_usd)
       if len(orders) > 0:
           return

       # Exit if we cannot trade
       if not data.can_trade(context.neo_usd):
           return

       # Another powerful built-in feature of the Catalyst backtester is the
       # portfolio object.  The portfolio object tracks your positions, cash,
       # cost basis of specific holdings, and more.  In this line, we calculate
       # how long or short our position is at this minute.   
       pos_amount = context.portfolio.positions[context.neo_usd].amount

       if rsi[-1] <= 30 and pos_amount == 0:
           log.info(
               '{}: buying - price: {}, rsi: {}'.format(
                   data.current_dt, price, rsi[-1]
               )
           )
           order_target_percent(context.neo_usd, 1)
           context.traded_today = True

       elif rsi[-1] >= 80 and pos_amount > 0:
           log.info(
               '{}: selling - price: {}, rsi: {}'.format(
                   data.current_dt, price, rsi[-1]
               )
           )
           order_target_percent(context.neo_usd, 0)
           context.traded_today = True


   def analyze(context=None, perf=None):
       import matplotlib.pyplot as plt

       # The base currency of the algo exchange
       base_currency = context.exchanges.values()[0].base_currency.upper()

       # Plot the portfolio value over time.
       ax1 = plt.subplot(611)
       perf.loc[:, 'portfolio_value'].plot(ax=ax1)
       ax1.set_ylabel('Portfolio Value ({})'.format(base_currency))

       # Plot the price increase or decrease over time.
       ax2 = plt.subplot(612, sharex=ax1)
       perf.loc[:, 'price'].plot(ax=ax2, label='Price')

       ax2.set_ylabel('{asset} ({base})'.format(
           asset=context.neo_usd.symbol, base=base_currency
       ))

       transaction_df = extract_transactions(perf)
       if not transaction_df.empty:
           buy_df = transaction_df[transaction_df['amount'] > 0]
           sell_df = transaction_df[transaction_df['amount'] < 0]
           ax2.scatter(
               buy_df.index.to_pydatetime(),
               perf.loc[buy_df.index, 'price'],
               marker='^',
               s=100,
               c='green',
               label=''
           )
           ax2.scatter(
               sell_df.index.to_pydatetime(),
               perf.loc[sell_df.index, 'price'],
               marker='v',
               s=100,
               c='red',
               label=''
           )

       ax4 = plt.subplot(613, sharex=ax1)
       perf.loc[:, 'cash'].plot(
           ax=ax4, label='Base Currency ({})'.format(base_currency)
       )
       ax4.set_ylabel('Cash ({})'.format(base_currency))

       perf['algorithm'] = perf.loc[:, 'algorithm_period_return']

       ax5 = plt.subplot(614, sharex=ax1)
       perf.loc[:, ['algorithm', 'price_change']].plot(ax=ax5)
       ax5.set_ylabel('Percent Change')

       ax6 = plt.subplot(615, sharex=ax1)
       perf.loc[:, 'rsi'].plot(ax=ax6, label='RSI')
       ax6.axhline(70, color='darkgoldenrod')
       ax6.axhline(30, color='darkgoldenrod')

       if not transaction_df.empty:
           ax6.scatter(
               buy_df.index.to_pydatetime(),
               perf.loc[buy_df.index, 'rsi'],
               marker='^',
               s=100,
               c='green',
               label=''
           )
           ax6.scatter(
               sell_df.index.to_pydatetime(),
               perf.loc[sell_df.index, 'rsi'],
               marker='v',
               s=100,
               c='red',
               label=''
           )
       plt.legend(loc=3)

       # Show the plot.
       plt.gcf().set_size_inches(18, 8)
       plt.show()
       pass


   if __name__ == '__main__':
       # The execution mode: backtest or live
       MODE = 'backtest'

       if MODE == 'backtest':
           # catalyst run -f catalyst/examples/mean_reversion_simple.py -x poloniex -s 2017-10-1 -e 2017-11-10 -c usdt -n mean-reversion --data-frequency minute --capital-base 10000
           run_algorithm(
               capital_base=10000,
               data_frequency='minute',
               initialize=initialize,
               handle_data=handle_data,
               analyze=analyze,
               exchange_name='bitfinex',
               algo_namespace=NAMESPACE,
               base_currency='usd',
               start=pd.to_datetime('2017-10-1', utc=True),
               end=pd.to_datetime('2017-11-10', utc=True),
           )

       elif MODE == 'live':
           run_algorithm(
               initialize=initialize,
               handle_data=handle_data,
               analyze=analyze,
               exchange_name='bitfinex',
               live=True,
               algo_namespace=NAMESPACE,
               base_currency='usd',
               live_graph=True
           )
