Catalyst Beginner Tutorial
--------------------------

Basics
~~~~~~

Catalyst is an open-source algorithmic trading simulator for crypto
assets written in Python. The source code can be found at: 
https://github.com/enigmampc/catalyst

Some benefits include:

-  Support for several of the top crypto-exchanges by trading volume.
-  Realistic: slippage, transaction costs, order delays.
-  Stream-based: Process each event individually, avoids look-ahead
   bias.
-  Batteries included: Common transforms (moving average) as well as
   common risk calculations (Sharpe).
-  Developed and continuously updated by
   `Enigma MPC <https://www.enigma.co>`__ which is building the Enigma 
   data marketplace protocol as well as Catalyst, the first application
   that will run on our protocol. Powered by our financial data 
   marketplace, Catalyst empowers users to share and curate data and 
   build profitable, data-driven investment strategies.

This tutorial assumes that you have Catalyst correctly installed, see the
:doc:`Install<install>` section if you haven't set up Catalyst yet.

Every ``catalyst`` algorithm consists of at least two functions you have to
define:

* ``initialize(context)``
* ``handle_data(context, data)``

Before the start of the algorithm, ``catalyst`` calls the
``initialize()`` function and passes in a ``context`` variable.
``context`` is a persistent namespace for you to store variables you
need to access from one algorithm iteration to the next.

After the algorithm has been initialized, ``catalyst`` calls the
``handle_data()`` function on each iteration, that's one per day (daily) or 
once every minute (minute), depending on the frequency we choose to run our 
simulation. On every iteration, ``handle_data()`` passes the same ``context`` 
variable and an event-frame called ``data`` containing the current trading bar 
with open, high, low, and close (OHLC) prices as well as volume for each 
crypto asset in your universe. 

.. For more information on these functions, see the `relevant part of the
.. Quantopian docs <https://www.quantopian.com/help#api-toplevel>`.

My first algorithm
~~~~~~~~~~~~~~~~~~

Lets take a look at a very simple algorithm from the ``examples`` directory: 
`buy_btc_simple.py <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/buy_btc_simple.py>`_:

.. code-block:: python

   from catalyst.api import order, record, symbol


   def initialize(context):
       context.asset = symbol('btc_usd')


   def handle_data(context, data):
       order(context.asset, 1)
       record(btc = data.current(context.asset, 'price'))


As you can see, we first have to import some functions we would like to
use. All functions commonly used in your algorithm can be found in
``catalyst.api``. Here we are using :func:`~catalyst.api.order()` which takes 
twoarguments: a cryptoasset object, and a number specifying how many assets you 
wouldlike to order (if negative, :func:`~catalyst.api.order()` will sell/short
assets). In this case we want to order 1 bitcoin at each iteration. 

.. For more documentation on ``order()``, see the `Quantopian docs
.. <https://www.quantopian.com/help#api-order>`__.

Finally, the :func:`~catalyst.api.record` function allows you to save the value
of a variable at each iteration. You provide it with a name for the variable
together with the variable itself: ``varname=var``. After the algorithm
finished running you will have access to each variable value you tracked
with :func:`~catalyst.api.record` under the name you provided (we will see this
further below). You also see how we can access the current price data of
a bitcoin in the ``data`` event frame.

.. (for more information see `here <https://www.quantopian.com/help#api-event-properties>`__.

Ingesting data
~~~~~~~~~~~~~~

Before you can backtest your algorithm, you first need to load the historical 
pricing data that Catalyst needs to run your simulation through a process called
``ingestion``. When you ingest data, Catalyst downloads that data in compressed 
form from the Enigma servers (which eventually will migrate to the Enigma Data 
Marketplace), and stores it locally to make it available at runtime. 

In order to ingest data, you need to run a command like the following:

.. code-block:: bash

  catalyst ingest-exchange -x bitfinex -i btc_usd

This instructs Catalyst to download pricing data from the ``Bitfinex`` exchange 
for the ``btc_usd`` currency pair (this follows from the simple algorithm 
presented above where we want to trade ``btc_usd``), and we're choosing to test
our algorithm using historical pricing data from the Bitfinex exchange. By 
default, Catalyst assumes that you want data with ``daily`` frequency (one candle
bar per day). If you want instead ``minute`` frequency (one candle bar for every
minute), you would need to specify it as follows:

.. code-block:: bash

  catalyst ingest-exchange -x bitfinex -i btc_usd -f minute

.. parsed-literal::

  Ingesting exchange bundle bitfinex...
    [====================================]  Ingesting daily price data on bitfinex:  100%

We believe it is important for you to have a high-level understanding of how 
data is managed, hence the following overview:

-  Pricing data is split and packaged into ``bundles``: chunks of data organized 
   as time series that are kept up to date daily on Enigma's servers. Catalyst 
   downloads the requested bundles and reconstructs the full dataset in your 
   hard drive.

-  Pricing data is provided in ``daily`` and ``minute`` resolution. Those are 
   different bundle datasets, and are managed separately.

-  Bundles are exchange-specific, as the pricing data is specific to the trades 
   that happen in each exchange. As a result, you can must specify which 
   exchange you want pricing data from when ingesting data

-  Catalyst keeps track of all the downloaded bundles, so that it only has to 
   download them once, and will do incremental updates as needed.

-  When running in ``live trading`` mode, Catalyst will first look for 
   historical pricing data in the locally stored bundles. If there is anything 
   missing, Catalyst will hit the exchange for the most recent data, and merge 
   it with the local bundle to optimize the number of requests it needs to make 
   to the exchange.

The ``ingest-exchange`` command in catalyst offers additional parameters to 
further tweak the data ingestion process. You can learn more by running the
following from the command line:

.. code-block:: bash

  catalyst ingest-exchange --help

Running the algorithm
~~~~~~~~~~~~~~~~~~~~~

You can now test your algorithm using cryptoassets' historical pricing data, 
``catalyst`` provides three interfaces: 

-  A command-line interface (CLI),
-  a :func:`~catalyst.run_algorithm()` that you can call from other 
   Python scripts,
-  and the ``Jupyter Notebook`` magic.


We'll start with the CLI, and introduce the ``run_algorithm()`` in the last 
example of this tutorial. Some of the :doc:`example algorithms <example-algos>` 
provide instructions on how to run them both from the CLI, and using the 
:func:`~catalyst.run_algorithm` function. For the third method, refer to the 
corresponding section on :doc:`Catalyst & Jupyter Notebook <jupyter>` after you 
have assimilated the contents of this tutorial.

Command line interface
^^^^^^^^^^^^^^^^^^^^^^

After you installed Catalyst, you should be able to execute the following
from your command line (e.g. ``cmd.exe`` or the ``Anaconda Prompt`` on Windows, 
or the Terminal application on MacOS). 

.. code-block:: bash

   $ catalyst --help

This is the resulting output, simplified for eductional purposes:

.. parsed-literal::

     Usage: catalyst [OPTIONS] COMMAND [ARGS]...

       Top level catalyst entry point.

     Options:
       --version               Show the version and exit.
       --help                  Show this message and exit.

     Commands:
       ingest-exchange  Ingest data for the given exchange.
       live             Trade live with the given algorithm.
       run              Run a backtest for the given algorithm.

There are three main modes you can run on Catalyst. The first being 
``ingest-exchange`` for data ingestion, which we have covered in the previous 
section. The second is ``live`` to use your algorithm to trade live against a 
given exchange, and the third mode ``run`` is to backtest your algorithm before 
trading live with it.

Let's start with backtesting, so run this other command to learn more about 
the available options:

.. code-block:: bash

   $ catalyst run --help

.. parsed-literal::

      Usage: catalyst run [OPTIONS]

        Run a backtest for the given algorithm.

      Options:
        -f, --algofile FILENAME         The file that contains the algorithm to run.
        -t, --algotext TEXT             The algorithm script to run.
        -D, --define TEXT               Define a name to be bound in the namespace
                                        before executing the algotext. For example
                                        '-Dname=value'. The value may be any python
                                        expression. These are evaluated in order so
                                        they may refer to previously defined names.
        --data-frequency [daily|minute]
                                        The data frequency of the simulation.
                                        [default: daily]
        --capital-base FLOAT            The starting capital for the simulation.
                                        [default: 10000000.0]
        -b, --bundle BUNDLE-NAME        The data bundle to use for the simulation.
                                        [default: poloniex]
        --bundle-timestamp TIMESTAMP    The date to lookup data on or before.
                                        [default: <current-time>]
        -s, --start DATE                The start date of the simulation.
        -e, --end DATE                  The end date of the simulation.
        -o, --output FILENAME           The location to write the perf data. If this
                                        is '-' the perf will be written to stdout.
                                        [default: -]
        --print-algo / --no-print-algo  Print the algorithm to stdout.
        -x, --exchange-name [poloniex|bitfinex|bittrex]
                                        The name of the targeted exchange
                                        (supported: bitfinex, bittrex, poloniex).
        -n, --algo-namespace TEXT       A label assigned to the algorithm for data
                                        storage purposes.
        -c, --base-currency TEXT        The base currency used to calculate
                                        statistics (e.g. usd, btc, eth).
        --help                          Show this message and exit.


As you can see there are a couple of flags that specify where to find your
algorithm (``-f``) as well as a the ``-x`` flag to specify which exchange to 
use. There are also arguments for the date range to run the algorithm over 
(``--start`` and ``--end``). You also need to set the base currency for your 
algorithm through the ``-c`` flag, and the ``--capital_base``. All the 
aforementioned parameters are required. Optionally, you will want to save the 
performance metrics of your algorithm so that you can analyze how it performed. 
This is done via the ``--output`` flag and will cause it to write the 
performance ``DataFrame`` in the pickle Python file format. Note that you can 
also define a configuration file with these parameters that you can then 
conveniently pass to the ``-c`` option so that you don't have to supply the 
command line args all the time.

Thus, to execute our algorithm from above and save the results to
``buy_btc_simple_out.pickle`` we would call ``catalyst run`` as follows:

.. code-block:: bash

    catalyst run -f buy_btc_simple.py -x bitfinex --start 2016-1-1 --end 2017-9-30 -c usd --capital-base 100000 -o buy_btc_simple_out.pickle


.. parsed-literal:: 

    INFO: run_algo: running algo in backtest mode
    INFO: exchange_algorithm: initialized trading algorithm in backtest mode
    INFO: Performance: Simulated 639 trading days out of 639.
    INFO: Performance: first open: 2016-01-01 00:00:00+00:00
    INFO: Performance: last close: 2017-09-30 23:59:00+00:00


``run`` first calls the ``initialize()`` function, and then
streams the historical asset price day-by-day through ``handle_data()``.
After each call to ``handle_data()`` we instruct ``catalyst`` to order 1
bitcoin. After the call of the ``order()`` function, ``catalyst``
enters the ordered stock and amount in the order book. After the
``handle_data()`` function has finished, ``catalyst`` looks for any open
orders and tries to fill them. If the trading volume is high enough for
this asset, the order is executed after adding the commission and
applying the slippage model which models the influence of your order on
the stock price, so your algorithm will be charged more than just the
asset price. (Note, that you can also change the commission and
slippage model that ``catalyst`` uses).

.. see the `Quantopian docs <https://www.quantopian.com/help#ide-slippage>`__
.. for more information).


Let's take a quick look at the performance ``DataFrame``. For this, we write 
different Python script--let's call it ``print_results.py``--and we make use of 
the fantastic ``pandas`` library to print the first ten rows. Note that 
``catalyst`` makes heavy usage of `pandas <http://pandas.pydata.org/>`_, 
especially for data analysis and outputting so it's worth spending some time to 
learn it.

.. code-block:: python

    import pandas as pd
    perf = pd.read_pickle('buy_btc_simple_out.pickle') # read in perf DataFrame
    print(perf.head())

Which we execute by running:

.. code-block:: bash

   $ python print_results.py

.. raw:: html

    <div style="max-height:1000px;max-width:1500px;overflow:auto;">
      <table border="1" class="dataframe">
        <thead>
          <tr style="text-align: right;">
            <th></th>
            <th>algo_volatility</th>
            <th>algorithm_period_return</th>
            <th>alpha</th>
            <th>benchmark_period_return</th>
            <th>benchmark_volatility</th>
            <th>beta</th>
            <th>btc</th>
            <th>capital_used</th>
            <th>ending_cash</th>
            <th>ending_exposure</th>
            <th>...</th>
            <th>short_exposure</th>
            <th>short_value</th>
            <th>shorts_count</th>
            <th>sortino</th>
            <th>starting_cash</th>
            <th>starting_exposure</th>
            <th>starting_value</th>
            <th>trading_days</th>
            <th>transactions</th>
            <th>treasury_period_return</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>2016-01-01 23:59:00+00:00</th>
            <td>NaN</td>
            <td>0.000000e+00</td>
            <td>NaN</td>
            <td>-0.010937</td>
            <td>NaN</td>
            <td>NaN</td>
            <td>433.979999</td>
            <td>0.000000</td>
            <td>1.000000e+07</td>
            <td>0.00</td>
            <td>...</td>
            <td>0</td>
            <td>0</td>
            <td>0</td>
            <td>NaN</td>
            <td>1.000000e+07</td>
            <td>0.00</td>
            <td>0.00</td>
            <td>1</td>
            <td>[]</td>
            <td>0.0227</td>
          </tr>
          <tr>
            <th>2016-01-02 23:59:00+00:00</th>
            <td>0.000011</td>
            <td>-9.536708e-07</td>
            <td>-0.000170</td>
            <td>-0.006480</td>
            <td>0.173338</td>
            <td>-0.000062</td>
            <td>432.700000</td>
            <td>-442.236708</td>
            <td>9.999558e+06</td>
            <td>432.70</td>
            <td>...</td>
            <td>0</td>
            <td>0</td>
            <td>0</td>
            <td>-11.224972</td>
            <td>1.000000e+07</td>
            <td>0.00</td>
            <td>0.00</td>
            <td>2</td>
            <td>[{u'order_id': u'7869f7828fa140328eb40477bb7de...</td>
            <td>0.0227</td>
          </tr>
          <tr>
            <th>2016-01-03 23:59:00+00:00</th>
            <td>0.000011</td>
            <td>-2.328842e-06</td>
            <td>-0.000176</td>
            <td>-0.026512</td>
            <td>0.197857</td>
            <td>0.000009</td>
            <td>428.390000</td>
            <td>-437.831716</td>
            <td>9.999120e+06</td>
            <td>856.78</td>
            <td>...</td>
            <td>0</td>
            <td>0</td>
            <td>0</td>
            <td>-12.754262</td>
            <td>9.999558e+06</td>
            <td>432.70</td>
            <td>432.70</td>
            <td>3</td>
            <td>[{u'order_id': u'be62ff77760c4599abaac43be9cc9...</td>
            <td>0.0227</td>
          </tr>
          <tr>
            <th>2016-01-04 23:59:00+00:00</th>
            <td>0.000011</td>
            <td>-2.380954e-06</td>
            <td>-0.000139</td>
            <td>-0.008640</td>
            <td>0.269790</td>
            <td>0.000020</td>
            <td>432.900000</td>
            <td>-442.441116</td>
            <td>9.998677e+06</td>
            <td>1298.70</td>
            <td>...</td>
            <td>0</td>
            <td>0</td>
            <td>0</td>
            <td>-11.287205</td>
            <td>9.999120e+06</td>
            <td>856.78</td>
            <td>856.78</td>
            <td>4</td>
            <td>[{u'order_id': u'd6dca79513214346a646079213526...</td>
            <td>0.0224</td>
          </tr>
          <tr>
            <th>2016-01-05 23:59:00+00:00</th>
            <td>0.000011</td>
            <td>-3.650729e-06</td>
            <td>-0.000158</td>
            <td>-0.021426</td>
            <td>0.245989</td>
            <td>0.000024</td>
            <td>431.840000</td>
            <td>-441.357754</td>
            <td>9.998236e+06</td>
            <td>1727.36</td>
            <td>...</td>
            <td>0</td>
            <td>0</td>
            <td>0</td>
            <td>-12.333847</td>
            <td>9.998677e+06</td>
            <td>1298.70</td>
            <td>1298.70</td>
            <td>5</td>
            <td>[{u'order_id': u'505275d6646a41f3856b22b16678d...</td>
            <td>0.0225</td>
          </tr>
        </tbody>
      </table>
    </div>

|
There is a row for each trading day, starting on the first day of our 
simulation Jan 1st, 2016. In the columns you can find various
information about the state of your algorithm. The column
``btc`` was placed there by the ``record()`` function mentioned earlier
and allows us to plot the price of bitcoin. For example, we could easily
examine now how our portfolio value changed over time compared to the
bitcoin price.

Now we will run the simulation again, but this time we extend our original 
algorithm with the addition of the ``analyze()`` function. Somewhat analogously 
as how ``initialize()`` gets called once before the start of the algorith, 
``analyze()`` gets called once at the end of the algorithm, and receives two 
variables: ``context``, which we discussed at the very beginning, and ``perf``, 
which is the pandas dataframe containing the performance data for our algorithm 
that we reviewed above. Inside the ``analyze()`` function is where we can 
analyze and visualize the results of our strategy. Here's the revised simple 
algorithm (note the addition of Line 1, and Lines 11-18)

.. code-block:: python

    import matplotlib.pyplot as plt
    from catalyst.api import order, record, symbol

    def initialize(context):
        context.asset = symbol('btc_usd')

    def handle_data(context, data):
        order(context.asset, 1)
        record(btc = data.current(context.asset, 'price'))

    def analyze(context, perf):
        ax1 = plt.subplot(211)
        perf.portfolio_value.plot(ax=ax1)
        ax1.set_ylabel('portfolio value')
        ax2 = plt.subplot(212, sharex=ax1)
        perf.btc.plot(ax=ax2)
        ax2.set_ylabel('bitcoin price')
        plt.show()

Here we make use of the external visualization library called 
`matplotlib <https://matplotlib.org/>`_, which you might recall we installed 
alongside enigma-catalyst (with the exception of the ``Conda`` install, where it
was included by default inside the conda environment we created). If for any 
reason you don't have it installed, you can add it by running:

.. code-block:: python

  (catalyst)$ pip install matplotlib

If everything works well, you'll see the following chart:

.. image:: https://s3.amazonaws.com/enigmaco-docs/github.io/buy_btc_simple_graph.png

Our algorithm performance as assessed by the ``portfolio_value`` closely 
matches that of the bitcoin price. This is not surprising as our algorithm 
only bought bitcoin every chance it got.

  If you get an error when invoking matplotlib to visualize the performance 
  results refer to `MacOS + Matplotlib <install.html#macos-virtualenv-matplotlib>`_. 
  Alternatively, some users have reported the following error when running an algo 
  in a Linux environment:

  .. parsed-literal::

      ImportError: No module named _tkinter, please install the python-tk package

  Which can easily solved by running (in Ubuntu/Debian-based systems):

  .. code-block:: python

      sudo apt install python-tk


.. _history:

Access to previous prices using ``history``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Working example: Dual Moving Average Cross-Over
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Dual Moving Average (DMA) is a classic momentum strategy. It's
probably not used by any serious trader anymore but is still very
instructive. The basic idea is that we compute two rolling or moving
averages (mavg) -- one with a longer window that is supposed to capture
long-term trends and one shorter window that is supposed to capture
short-term trends. Once the short-mavg crosses the long-mavg from below
we assume that the stock price has upwards momentum and long the stock.
If the short-mavg crosses from above we exit the positions as we assume
the stock to go down further.

As we need to have access to previous prices to implement this strategy
we need a new concept: History. ``data.history()`` is a convenience function 
that keeps a rolling window of data for you. The first argument is the number 
of bars you want to collect, the second argument is the unit (either ``'1d'`` 
for daily or ``'1m'`` for minute frequency, but note that you need to have 
minute-level data when using ``1m``). This is a function we use in the 
``handle_data()`` section.

You will note that the code below is substantially longer than the previous 
examples. Don't get overwhelmed by it as the logic is fairly simple and easy to 
follow. Most of the added some complexity has been added to beautify the output, 
which you can skim through for now. A copy of this algorithm is available in 
the ``examples`` directory:
`dual_moving_average.py <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/dual_moving_average.py>`_.

.. code-block:: python

    import numpy as np
    import pandas as pd
    from logbook import Logger
    import matplotlib.pyplot as plt 

    from catalyst import run_algorithm
    from catalyst.api import (order, record, symbol, order_target_percent, 
            get_open_orders)
    from catalyst.exchange.stats_utils import extract_transactions

    NAMESPACE = 'dual_moving_average'
    log = Logger(NAMESPACE)

    def initialize(context):
        context.i = 0
        context.asset = symbol('ltc_usd')
        context.base_price = None


    def handle_data(context, data):
        # define the windows for the moving averages 
        short_window = 50
        long_window = 200

        # Skip as many bars as long_window to properly compute the average
        context.i += 1
        if context.i < long_window:
           return

        # Compute moving averages calling data.history() for each 
        # moving average with the appropriate parameters. We choose to use
        # minute bars for this simulation -> freq="1m"
        # Returns a pandas dataframe.
        short_mavg = data.history(context.asset, 'price', 
                            bar_count=short_window, frequency="1m").mean()
        long_mavg = data.history(context.asset, 'price',
                            bar_count=long_window, frequency="1m").mean()

        # Let's keep the price of our asset in a more handy variable
        price = data.current(context.asset, 'price')

        # If base_price is not set, we use the current value. This is the
        # price at the first bar which we reference to calculate price_change.
        if context.base_price is None:
            context.base_price = price
        price_change = (price - context.base_price) / context.base_price

        # Save values for later inspection
        record(price=price,
               cash=context.portfolio.cash,
               price_change=price_change,
               short_mavg=short_mavg,
               long_mavg=long_mavg)

        # Since we are using limit orders, some orders may not execute immediately
        # we wait until all orders are executed before considering more trades.
        orders = get_open_orders(context.asset)
        if len(orders) > 0:
            return

        # Exit if we cannot trade
        if not data.can_trade(context.asset):
            return

        # We check what's our position on our portfolio and trade accordingly
        pos_amount = context.portfolio.positions[context.asset].amount

        # Trading logic
        if short_mavg > long_mavg and pos_amount == 0:
           # we buy 100% of our portfolio for this asset
           order_target_percent(context.asset, 1)
        elif short_mavg < long_mavg and pos_amount > 0:
           # we sell all our positions for this asset
           order_target_percent(context.asset, 0)


    def analyze(context, perf):

        # Get the base_currency that was passed as a parameter to the simulation
        base_currency = context.exchanges.values()[0].base_currency.upper()

        # First chart: Plot portfolio value using base_currency
        ax1 = plt.subplot(411)
        perf.loc[:, ['portfolio_value']].plot(ax=ax1)
        ax1.legend_.remove()
        ax1.set_ylabel('Portfolio Value\n({})'.format(base_currency))
        start, end = ax1.get_ylim()
        ax1.yaxis.set_ticks(np.arange(start, end, (end-start)/5))

        # Second chart: Plot asset price, moving averages and buys/sells
        ax2 = plt.subplot(412, sharex=ax1)
        perf.loc[:, ['price','short_mavg','long_mavg']].plot(ax=ax2, label='Price')
        ax2.legend_.remove()
        ax2.set_ylabel('{asset}\n({base})'.format(
            asset = context.asset.symbol,
            base = base_currency
            ))
        start, end = ax2.get_ylim()
        ax2.yaxis.set_ticks(np.arange(start, end, (end-start)/5))

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

        # Third chart: Compare percentage change between our portfolio
        # and the price of the asset
        ax3 = plt.subplot(413, sharex=ax1)
        perf.loc[:, ['algorithm_period_return', 'price_change']].plot(ax=ax3)
        ax3.legend_.remove()
        ax3.set_ylabel('Percent Change')
        start, end = ax3.get_ylim()
        ax3.yaxis.set_ticks(np.arange(start, end, (end-start)/5))

        # Fourth chart: Plot our cash
        ax4 = plt.subplot(414, sharex=ax1)
        perf.cash.plot(ax=ax4)
        ax4.set_ylabel('Cash\n({})'.format(base_currency))
        start, end = ax4.get_ylim()
        ax4.yaxis.set_ticks(np.arange(0, end, end/5))

        plt.show()


    if __name__ == '__main__':
        run_algorithm(
                capital_base=1000,
                data_frequency='minute',
                initialize=initialize,
                handle_data=handle_data,
                analyze=analyze,
                exchange_name='bitfinex',
                algo_namespace=NAMESPACE,
                base_currency='usd',
                start=pd.to_datetime('2017-9-22', utc=True),
                end=pd.to_datetime('2017-9-23', utc=True),
            )

In order to run the code above, you have to ingest the needed data first:

.. code-block:: bash

  catalyst ingest-exchange -x bitfinex -f minute -i ltc_usd

And then run the code above with the following command:

.. code-block:: bash

  catalyst run -f dual_moving_average.py -x bitfinex -s 2017-9-22 -e 2017-9-23 --capital-base 1000 --base-currency usd --data-frequency minute -o out.pickle

Alternatively, we can make use of the ``run_algorithm()`` function included at 
the end of the file, where we can specify all the simulation parameters, and 
execute this file as a Python script:

.. code-block:: bash

  python dual_moving_average.py

Either way, we obtain the following charts:

.. image:: https://s3.amazonaws.com/enigmaco-docs/github.io/tutorial_dual_moving_average.png


A few comments on the code above:

  At the beginning of our code, we import a number of Python libraries that we
  will be using in different parts of our script. It's good practice to keep all
  imports at the beginning of the file, as they are available globally 
  throughout our script. All the libraries imported in this example are already
  present in your environment since they are prerequisites for the Catalyst 
  installation.

  Focus on the code that is inside ``handle_data()`` that is where all the 
  trading logic occurs. You can safely dismiss most of the code in the 
  ``analyze()`` section, which is mostly to customize the visualization of the 
  performance of our algorithm using the matplotlib library. You can copy and
  paste this whole section into other algorithms to obtain a similar display.

  Inside the ``handle_data()``, we also used the ``order_target_percent()`` 
  function above. This and other functions like it can make order management 
  and portfolio rebalancing much easier.

  The ``ltc_usd`` asset was arbitrarily chosen. The values of 50 and 200 for the 
  ``short_window`` and ``long_window`` parameters are fairly common for a dual 
  moving average crossover strategy from the world of traditional stocks (but 
  bear in mind that they are usually used with daily bars instead of minute 
  bars). The ``start`` and ``end`` dates have been chosen so as to demonstrate 
  how our strategy can both perform better (blue line above green line on the 
  ``Percent Change`` chart) and worse (green line above blue line towards the end) than the
  price of the asset we are trading. 

  You can change any of these parameters: ``asset``, ``short_window``, 
  ``long_window``, ``start_date`` and ``end_date`` and compare the results, and 
  you will see that in most cases, the performance is either worse than the 
  price of the asset, or you are overfitting to one specific case. As we said 
  at the beginning of this section, this strategy is probably not used by any 
  serious trader anymore, but its educational purpose.

Although it might not be directly apparent, the power of ``history()``
(pun intended) can not be under-estimated as most algorithms make use of
prior market developments in one form or another. You could easily
devise a strategy that trains a classifier with
`scikit-learn <http://scikit-learn.org/stable/>`__ which tries to
predict future market movements based on past prices (note, that most of
the ``scikit-learn`` functions require ``numpy.ndarray``\ s rather than
``pandas.DataFrame``\ s, so you can simply pass the underlying
``ndarray`` of a ``DataFrame`` via ``.values``).


Next steps
~~~~~~~~~~

We hope that this tutorial gave you a little insight into the
architecture, API, and features of Catalyst. For next steps, check
out some of the other :doc:`example algorithms<example-algos>`.

Feel free to ask questions on the ``#catalyst_dev`` channel of our 
`Discord group <https://discord.gg/SJK32GY>`__ and report
problems on our `GitHub issue tracker <https://github.com/enigmampc/catalyst/issues>`__.
