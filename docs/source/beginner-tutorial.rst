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
two arguments: a cryptoasset object, and a number specifying how many assets you
would like to order (if negative, :func:`~catalyst.api.order()` will sell
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
   that happen in each exchange. As a result, you must specify which 
   exchange you want pricing data from when ingesting data.

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
corresponding section on :ref:`Catalyst & Jupyter Notebook <jupyter>` after you 
have assimilated the contents of this tutorial.

Command line interface
^^^^^^^^^^^^^^^^^^^^^^

After you installed Catalyst, you should be able to execute the following
from your command line (e.g. ``cmd.exe`` or the ``Anaconda Prompt`` on Windows, 
or the Terminal application on MacOS). 

.. code-block:: bash

   $ catalyst --help

This is the resulting output, simplified for educational purposes:

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
        -x, --exchange-name [poloniex|bitfinex|bittrex|binance]
                                        The name of the targeted exchange
                                        (supported: binance, bitfinex, bittrex, poloniex).
        -n, --algo-namespace TEXT       A label assigned to the algorithm for data
                                        storage purposes.
        -c, --quote-currency TEXT        The quote currency used to calculate
                                        statistics (e.g. usd, btc, eth).
        --help                          Show this message and exit.


As you can see there are a couple of flags that specify where to find your
algorithm (``-f``) as well as a the ``-x`` flag to specify which exchange to 
use. There are also arguments for the date range to run the algorithm over 
(``--start`` and ``--end``). You also need to set the quote currency for your
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
as how ``initialize()`` gets called once before the start of the algorithm, 
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

.. code-block:: bash

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

.. literalinclude:: ../../catalyst/examples/dual_moving_average.py
   :language: python

In order to run the code above, you have to ingest the needed data first:

.. code-block:: bash

  catalyst ingest-exchange -x bitfinex -f minute -i ltc_usd

And then run the code above with the following command:

.. code-block:: bash

  catalyst run -f dual_moving_average.py -x bitfinex -s 2017-9-22 -e 2017-9-23 --capital-base 1000 --quote-currency usd --data-frequency minute -o out.pickle

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
  serious trader anymore, but it has an educational purpose.

Although it might not be directly apparent, the power of ``history()``
(pun intended) can not be under-estimated as most algorithms make use of
prior market developments in one form or another. You could easily
devise a strategy that trains a classifier with
`scikit-learn <http://scikit-learn.org/stable/>`__ which tries to
predict future market movements based on past prices (note, that most of
the ``scikit-learn`` functions require ``numpy.ndarray``\ s rather than
``pandas.DataFrame``\ s, so you can simply pass the underlying
``ndarray`` of a ``DataFrame`` via ``.values``).

.. _jupyter:

Jupyter Notebook
~~~~~~~~~~~~~~~~

(`This is actual Notebook <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/running_catalyst_in_jupyter_notebook.ipynb>`_ referenced in the text below)

The `Jupyter Notebook <https://jupyter.org/>`__ is a very powerful
browser-based interface to a Python interpreter. As it is already the
de-facto interface for most quantitative researchers, ``catalyst``
provides an easy way to run your algorithm inside the Notebook without
requiring you to use the CLI. We include this section here as an alternative to
running algorithms through the command line.

Install
^^^^^^^

In order to use Jupyter Notebook, you first have to install it inside your
environment. It's available as ``pip`` package, so regardless of how you 
installed Catalyst, go inside your catalyst environment and run:

.. code-block:: bash

    (catalyst)$ pip install jupyter

Once you have Jupyter Notebook installed, every time you want to use it run:

.. code-block:: bash

    (catalyst)$ jupyter notebook

A local server will launch, and will open a new window on your browser. That's
the interface through which you will interact with Jupyter Notebook.

Running Algorithms
^^^^^^^^^^^^^^^^^^

Before running your algorithms inside the Jupyter Notebook, remember to ingest
the data from the command line interface (CLI). In the example below, you would
need to run first:

.. code-block:: bash

  catalyst ingest-exchange -x bitfinex -i btc_usd

To use Catalyst inside a Jupyter Noebook, you have to write your algorithm in a 
cell and let the Jupyter know that it is supposed to execute this algorithm with 
Catalyst. This is done via the ``%%catalyst`` IPython magic command that is 
available after you import ``catalyst`` from within the Notebook. This magic 
takes the same arguments as the command line interface. Thus to run the
algorithm just supply the same parameters as the CLI but without the -f
and -o arguments. We just have to execute the following cell after
importing ``catalyst`` to register the magic.

.. code:: python

    # Register the catalyst magic
    %load_ext catalyst

.. code:: python

    # Setup matplotlib to display graphs inline in this Notebook
    %matplotlib inline

Note below that we do not have to specify an input file (-f) since the
magic will use the contents of the cell and look for your algorithm
functions.

.. code:: python

    %%catalyst --start 2015-3-2 --end 2017-6-28 --capital-base 100000 -x bitfinex -c usd

    from catalyst.finance.slippage import VolumeShareSlippage

    from catalyst.api import (
        order_target_value,
        symbol,
        record,
        cancel_order,
        get_open_orders,
    )

    def initialize(context):
        context.ASSET_NAME = 'btc_usd'
        context.TARGET_HODL_RATIO = 0.8
        context.RESERVE_RATIO = 1.0 - context.TARGET_HODL_RATIO

        # For all trading pairs in the poloniex bundle, the default denomination
        # currently supported by Catalyst is 1/1000th of a full coin. Use this
        # constant to scale the price of up to that of a full coin if desired.
        context.TICK_SIZE = 1000.0

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
                limit_price=price*1.1,
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
        (context.TICK_SIZE * results[['price']]).plot(ax=ax2)

        trans = results.ix[[t != [] for t in results.transactions]]
        buys = trans.ix[
            [t[0]['amount'] > 0 for t in trans.transactions]
        ]
        ax2.plot(
            buys.index,
            context.TICK_SIZE * results.price[buys.index],
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

::

    [2017-08-11 07:19:46.411748] INFO: Loader: Loading benchmark data for 'USDT_BTC' from 1989-12-31 00:00:00+00:00 to 2017-08-09 00:00:00+00:00
    [2017-08-11 07:19:46.418983] INFO: Loader: Loading data for /Users/<snipped>/.catalyst/data/USDT_BTC_benchmark.csv failed with error [Unknown string format].
    [2017-08-11 07:19:46.419740] INFO: Loader: Cache at /Users/<snipped>/.catalyst/data/USDT_BTC_benchmark.csv does not have data from 1990-01-01 00:00:00+00:00 to 2017-08-09 00:00:00+00:00.

    [2017-08-11 07:19:46.420770] INFO: Loader: Downloading benchmark data for 'USDT_BTC' from 1989-12-31 00:00:00+00:00 to 2017-08-09 00:00:00+00:00
    [2017-08-11 07:19:50.060244] WARNING: Loader: Still don't have expected data after redownload!
    [2017-08-11 07:19:50.097334] WARNING: Loader: Refusing to download new treasury data because a download succeeded at 2017-08-11 06:56:49+00:00.
    [2017-08-11 07:19:54.618399] INFO: Performance: Simulated 851 trading days out of 851.
    [2017-08-11 07:19:54.619301] INFO: Performance: first open: 2015-03-01 00:00:00+00:00
    [2017-08-11 07:19:54.620430] INFO: Performance: last close: 2017-06-28 23:59:00+00:00

.. figure:: https://i.imgur.com/DS5w47q.png
   :alt: png

.. raw:: html

   <div>

.. raw:: html

   <table border="1" class="dataframe">

.. raw:: html

   <thead>

.. raw:: html

   <tr style="text-align: right;">

.. raw:: html

   <th>

.. raw:: html

   </th>

.. raw:: html

   <th>

algo_volatility

.. raw:: html

   </th>

.. raw:: html

   <th>

algorithm_period_return

.. raw:: html

   </th>

.. raw:: html

   <th>

alpha

.. raw:: html

   </th>

.. raw:: html

   <th>

benchmark_period_return

.. raw:: html

   </th>

.. raw:: html

   <th>

benchmark_volatility

.. raw:: html

   </th>

.. raw:: html

   <th>

beta

.. raw:: html

   </th>

.. raw:: html

   <th>

capital_used

.. raw:: html

   </th>

.. raw:: html

   <th>

cash

.. raw:: html

   </th>

.. raw:: html

   <th>

ending_cash

.. raw:: html

   </th>

.. raw:: html

   <th>

ending_exposure

.. raw:: html

   </th>

.. raw:: html

   <th>

…

.. raw:: html

   </th>

.. raw:: html

   <th>

starting_cash

.. raw:: html

   </th>

.. raw:: html

   <th>

starting_exposure

.. raw:: html

   </th>

.. raw:: html

   <th>

starting_value

.. raw:: html

   </th>

.. raw:: html

   <th>

trading_days

.. raw:: html

   </th>

.. raw:: html

   <th>

transactions

.. raw:: html

   </th>

.. raw:: html

   <th>

treasury_period_return

.. raw:: html

   </th>

.. raw:: html

   <th>

volume

.. raw:: html

   </th>

.. raw:: html

   <th>

treasury

.. raw:: html

   </th>

.. raw:: html

   <th>

algorithm

.. raw:: html

   </th>

.. raw:: html

   <th>

benchmark

.. raw:: html

   </th>

.. raw:: html

   </tr>

.. raw:: html

   </thead>

.. raw:: html

   <tbody>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-01 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

NaN

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

NaN

.. raw:: html

   </td>

.. raw:: html

   <td>

0.045833

.. raw:: html

   </td>

.. raw:: html

   <td>

NaN

.. raw:: html

   </td>

.. raw:: html

   <td>

NaN

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000

.. raw:: html

   </td>

.. raw:: html

   <td>

1

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0200

.. raw:: html

   </td>

.. raw:: html

   <td>

317

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0200

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

0.045833

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-02 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.000278

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.000025

.. raw:: html

   </td>

.. raw:: html

   <td>

0.011045

.. raw:: html

   </td>

.. raw:: html

   <td>

0.120833

.. raw:: html

   </td>

.. raw:: html

   <td>

0.290503

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.000956

.. raw:: html

   </td>

.. raw:: html

   <td>

-85544.474955

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

85542.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000

.. raw:: html

   </td>

.. raw:: html

   <td>

2

.. raw:: html

   </td>

.. raw:: html

   <td>

[{u’commission’: None, u’amount’: 318, u’sid’:…

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0208

.. raw:: html

   </td>

.. raw:: html

   <td>

98063

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0208

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.000025

.. raw:: html

   </td>

.. raw:: html

   <td>

0.120833

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-03 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.051796

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.005688

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.197544

.. raw:: html

   </td>

.. raw:: html

   <td>

0.113416

.. raw:: html

   </td>

.. raw:: html

   <td>

0.633538

.. raw:: html

   </td>

.. raw:: html

   <td>

0.077239

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

84975.642

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

85542.000

.. raw:: html

   </td>

.. raw:: html

   <td>

85542.000

.. raw:: html

   </td>

.. raw:: html

   <td>

3

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0212

.. raw:: html

   </td>

.. raw:: html

   <td>

442983

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0212

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.005688

.. raw:: html

   </td>

.. raw:: html

   <td>

0.113416

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-04 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.342118

.. raw:: html

   </td>

.. raw:: html

   <td>

0.034955

.. raw:: html

   </td>

.. raw:: html

   <td>

0.401861

.. raw:: html

   </td>

.. raw:: html

   <td>

0.166666

.. raw:: html

   </td>

.. raw:: html

   <td>

0.524400

.. raw:: html

   </td>

.. raw:: html

   <td>

0.181468

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

89040.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

84975.642

.. raw:: html

   </td>

.. raw:: html

   <td>

84975.642

.. raw:: html

   </td>

.. raw:: html

   <td>

4

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0212

.. raw:: html

   </td>

.. raw:: html

   <td>

245889

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0212

.. raw:: html

   </td>

.. raw:: html

   <td>

0.034955

.. raw:: html

   </td>

.. raw:: html

   <td>

0.166666

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-05 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.637226

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.038185

.. raw:: html

   </td>

.. raw:: html

   <td>

-3.914003

.. raw:: html

   </td>

.. raw:: html

   <td>

0.070834

.. raw:: html

   </td>

.. raw:: html

   <td>

0.976896

.. raw:: html

   </td>

.. raw:: html

   <td>

0.550520

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

81726.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

89040.000

.. raw:: html

   </td>

.. raw:: html

   <td>

89040.000

.. raw:: html

   </td>

.. raw:: html

   <td>

5

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0211

.. raw:: html

   </td>

.. raw:: html

   <td>

117440

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0211

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.038185

.. raw:: html

   </td>

.. raw:: html

   <td>

0.070834

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-06 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.580521

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.028645

.. raw:: html

   </td>

.. raw:: html

   <td>

-3.100822

.. raw:: html

   </td>

.. raw:: html

   <td>

0.083333

.. raw:: html

   </td>

.. raw:: html

   <td>

0.874082

.. raw:: html

   </td>

.. raw:: html

   <td>

0.546703

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

82680.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

81726.000

.. raw:: html

   </td>

.. raw:: html

   <td>

81726.000

.. raw:: html

   </td>

.. raw:: html

   <td>

6

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0224

.. raw:: html

   </td>

.. raw:: html

   <td>

84197

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0224

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.028645

.. raw:: html

   </td>

.. raw:: html

   <td>

0.083333

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-07 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.530557

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.028645

.. raw:: html

   </td>

.. raw:: html

   <td>

-2.625704

.. raw:: html

   </td>

.. raw:: html

   <td>

0.083333

.. raw:: html

   </td>

.. raw:: html

   <td>

0.802793

.. raw:: html

   </td>

.. raw:: html

   <td>

0.536589

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

82680.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

82680.000

.. raw:: html

   </td>

.. raw:: html

   <td>

82680.000

.. raw:: html

   </td>

.. raw:: html

   <td>

7

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0224

.. raw:: html

   </td>

.. raw:: html

   <td>

181

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0224

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.028645

.. raw:: html

   </td>

.. raw:: html

   <td>

0.083333

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-08 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.491628

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.028645

.. raw:: html

   </td>

.. raw:: html

   <td>

-2.276841

.. raw:: html

   </td>

.. raw:: html

   <td>

0.083333

.. raw:: html

   </td>

.. raw:: html

   <td>

0.746605

.. raw:: html

   </td>

.. raw:: html

   <td>

0.529163

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

82680.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

82680.000

.. raw:: html

   </td>

.. raw:: html

   <td>

82680.000

.. raw:: html

   </td>

.. raw:: html

   <td>

8

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0224

.. raw:: html

   </td>

.. raw:: html

   <td>

30900

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0224

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.028645

.. raw:: html

   </td>

.. raw:: html

   <td>

0.083333

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-09 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.467885

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.015925

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.895269

.. raw:: html

   </td>

.. raw:: html

   <td>

0.100000

.. raw:: html

   </td>

.. raw:: html

   <td>

0.698764

.. raw:: html

   </td>

.. raw:: html

   <td>

0.532652

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

83952.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

82680.000

.. raw:: html

   </td>

.. raw:: html

   <td>

82680.000

.. raw:: html

   </td>

.. raw:: html

   <td>

9

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0220

.. raw:: html

   </td>

.. raw:: html

   <td>

128367

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0220

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.015925

.. raw:: html

   </td>

.. raw:: html

   <td>

0.100000

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-10 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.626552

.. raw:: html

   </td>

.. raw:: html

   <td>

0.069935

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.625285

.. raw:: html

   </td>

.. raw:: html

   <td>

0.212500

.. raw:: html

   </td>

.. raw:: html

   <td>

0.800983

.. raw:: html

   </td>

.. raw:: html

   <td>

0.676289

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

92538.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

83952.000

.. raw:: html

   </td>

.. raw:: html

   <td>

83952.000

.. raw:: html

   </td>

.. raw:: html

   <td>

10

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0214

.. raw:: html

   </td>

.. raw:: html

   <td>

54961

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0214

.. raw:: html

   </td>

.. raw:: html

   <td>

0.069935

.. raw:: html

   </td>

.. raw:: html

   <td>

0.212500

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-11 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.644515

.. raw:: html

   </td>

.. raw:: html

   <td>

0.022235

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.727710

.. raw:: html

   </td>

.. raw:: html

   <td>

0.150000

.. raw:: html

   </td>

.. raw:: html

   <td>

0.834650

.. raw:: html

   </td>

.. raw:: html

   <td>

0.684052

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

87768.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

92538.000

.. raw:: html

   </td>

.. raw:: html

   <td>

92538.000

.. raw:: html

   </td>

.. raw:: html

   <td>

11

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0211

.. raw:: html

   </td>

.. raw:: html

   <td>

42511

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0211

.. raw:: html

   </td>

.. raw:: html

   <td>

0.022235

.. raw:: html

   </td>

.. raw:: html

   <td>

0.150000

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-12 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.614650

.. raw:: html

   </td>

.. raw:: html

   <td>

0.022235

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.573455

.. raw:: html

   </td>

.. raw:: html

   <td>

0.150000

.. raw:: html

   </td>

.. raw:: html

   <td>

0.798403

.. raw:: html

   </td>

.. raw:: html

   <td>

0.680882

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

87768.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

87768.000

.. raw:: html

   </td>

.. raw:: html

   <td>

87768.000

.. raw:: html

   </td>

.. raw:: html

   <td>

12

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0210

.. raw:: html

   </td>

.. raw:: html

   <td>

2909

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0210

.. raw:: html

   </td>

.. raw:: html

   <td>

0.022235

.. raw:: html

   </td>

.. raw:: html

   <td>

0.150000

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-13 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.588942

.. raw:: html

   </td>

.. raw:: html

   <td>

0.019405

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.454733

.. raw:: html

   </td>

.. raw:: html

   <td>

0.146291

.. raw:: html

   </td>

.. raw:: html

   <td>

0.767688

.. raw:: html

   </td>

.. raw:: html

   <td>

0.677881

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

87484.980

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

87768.000

.. raw:: html

   </td>

.. raw:: html

   <td>

87768.000

.. raw:: html

   </td>

.. raw:: html

   <td>

13

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0213

.. raw:: html

   </td>

.. raw:: html

   <td>

57613

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0213

.. raw:: html

   </td>

.. raw:: html

   <td>

0.019405

.. raw:: html

   </td>

.. raw:: html

   <td>

0.146291

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-14 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.565911

.. raw:: html

   </td>

.. raw:: html

   <td>

0.019373

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.344915

.. raw:: html

   </td>

.. raw:: html

   <td>

0.146250

.. raw:: html

   </td>

.. raw:: html

   <td>

0.739230

.. raw:: html

   </td>

.. raw:: html

   <td>

0.675665

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

87481.800

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

87484.980

.. raw:: html

   </td>

.. raw:: html

   <td>

87484.980

.. raw:: html

   </td>

.. raw:: html

   <td>

14

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0213

.. raw:: html

   </td>

.. raw:: html

   <td>

48310

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0213

.. raw:: html

   </td>

.. raw:: html

   <td>

0.019373

.. raw:: html

   </td>

.. raw:: html

   <td>

0.146250

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-15 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.551394

.. raw:: html

   </td>

.. raw:: html

   <td>

0.041659

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.191436

.. raw:: html

   </td>

.. raw:: html

   <td>

0.175450

.. raw:: html

   </td>

.. raw:: html

   <td>

0.714876

.. raw:: html

   </td>

.. raw:: html

   <td>

0.680484

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

89710.344

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

87481.800

.. raw:: html

   </td>

.. raw:: html

   <td>

87481.800

.. raw:: html

   </td>

.. raw:: html

   <td>

15

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0213

.. raw:: html

   </td>

.. raw:: html

   <td>

29454

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0213

.. raw:: html

   </td>

.. raw:: html

   <td>

0.041659

.. raw:: html

   </td>

.. raw:: html

   <td>

0.175450

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-16 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.541846

.. raw:: html

   </td>

.. raw:: html

   <td>

0.019055

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.188212

.. raw:: html

   </td>

.. raw:: html

   <td>

0.145833

.. raw:: html

   </td>

.. raw:: html

   <td>

0.706049

.. raw:: html

   </td>

.. raw:: html

   <td>

0.680281

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

87450.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

89710.344

.. raw:: html

   </td>

.. raw:: html

   <td>

89710.344

.. raw:: html

   </td>

.. raw:: html

   <td>

16

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0210

.. raw:: html

   </td>

.. raw:: html

   <td>

25564

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0210

.. raw:: html

   </td>

.. raw:: html

   <td>

0.019055

.. raw:: html

   </td>

.. raw:: html

   <td>

0.145833

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-17 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.524682

.. raw:: html

   </td>

.. raw:: html

   <td>

0.019055

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.115149

.. raw:: html

   </td>

.. raw:: html

   <td>

0.145833

.. raw:: html

   </td>

.. raw:: html

   <td>

0.684599

.. raw:: html

   </td>

.. raw:: html

   <td>

0.678870

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

87450.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

87450.000

.. raw:: html

   </td>

.. raw:: html

   <td>

87450.000

.. raw:: html

   </td>

.. raw:: html

   <td>

17

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0206

.. raw:: html

   </td>

.. raw:: html

   <td>

9

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0206

.. raw:: html

   </td>

.. raw:: html

   <td>

0.019055

.. raw:: html

   </td>

.. raw:: html

   <td>

0.145833

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-18 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.532621

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.021999

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.180440

.. raw:: html

   </td>

.. raw:: html

   <td>

0.092041

.. raw:: html

   </td>

.. raw:: html

   <td>

0.696261

.. raw:: html

   </td>

.. raw:: html

   <td>

0.685307

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

83344.620

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

87450.000

.. raw:: html

   </td>

.. raw:: html

   <td>

87450.000

.. raw:: html

   </td>

.. raw:: html

   <td>

18

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0193

.. raw:: html

   </td>

.. raw:: html

   <td>

164911

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0193

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.021999

.. raw:: html

   </td>

.. raw:: html

   <td>

0.092041

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-19 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.518811

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.013234

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.096387

.. raw:: html

   </td>

.. raw:: html

   <td>

0.103526

.. raw:: html

   </td>

.. raw:: html

   <td>

0.676861

.. raw:: html

   </td>

.. raw:: html

   <td>

0.686186

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

84221.028

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

83344.620

.. raw:: html

   </td>

.. raw:: html

   <td>

83344.620

.. raw:: html

   </td>

.. raw:: html

   <td>

19

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0198

.. raw:: html

   </td>

.. raw:: html

   <td>

713904

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0198

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.013234

.. raw:: html

   </td>

.. raw:: html

   <td>

0.103526

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-20 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.505168

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.017324

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.050273

.. raw:: html

   </td>

.. raw:: html

   <td>

0.098170

.. raw:: html

   </td>

.. raw:: html

   <td>

0.659945

.. raw:: html

   </td>

.. raw:: html

   <td>

0.685070

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

83812.080

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

84221.028

.. raw:: html

   </td>

.. raw:: html

   <td>

84221.028

.. raw:: html

   </td>

.. raw:: html

   <td>

20

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0193

.. raw:: html

   </td>

.. raw:: html

   <td>

132725

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0193

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.017324

.. raw:: html

   </td>

.. raw:: html

   <td>

0.098170

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-21 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.492384

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.018494

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.002051

.. raw:: html

   </td>

.. raw:: html

   <td>

0.096637

.. raw:: html

   </td>

.. raw:: html

   <td>

0.643679

.. raw:: html

   </td>

.. raw:: html

   <td>

0.684283

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

83695.056

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

83812.080

.. raw:: html

   </td>

.. raw:: html

   <td>

83812.080

.. raw:: html

   </td>

.. raw:: html

   <td>

21

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0193

.. raw:: html

   </td>

.. raw:: html

   <td>

201155

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0193

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.018494

.. raw:: html

   </td>

.. raw:: html

   <td>

0.096637

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-22 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.482998

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.004744

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.927947

.. raw:: html

   </td>

.. raw:: html

   <td>

0.114653

.. raw:: html

   </td>

.. raw:: html

   <td>

0.629319

.. raw:: html

   </td>

.. raw:: html

   <td>

0.686478

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

85070.088

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

83695.056

.. raw:: html

   </td>

.. raw:: html

   <td>

83695.056

.. raw:: html

   </td>

.. raw:: html

   <td>

22

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0193

.. raw:: html

   </td>

.. raw:: html

   <td>

64378

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0193

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.004744

.. raw:: html

   </td>

.. raw:: html

   <td>

0.114653

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-23 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.477523

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.026505

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.935352

.. raw:: html

   </td>

.. raw:: html

   <td>

0.086139

.. raw:: html

   </td>

.. raw:: html

   <td>

0.623502

.. raw:: html

   </td>

.. raw:: html

   <td>

0.687025

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

82894.014

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

85070.088

.. raw:: html

   </td>

.. raw:: html

   <td>

85070.088

.. raw:: html

   </td>

.. raw:: html

   <td>

23

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0192

.. raw:: html

   </td>

.. raw:: html

   <td>

61850

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0192

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.026505

.. raw:: html

   </td>

.. raw:: html

   <td>

0.086139

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-24 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.504086

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.084215

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.021023

.. raw:: html

   </td>

.. raw:: html

   <td>

0.010523

.. raw:: html

   </td>

.. raw:: html

   <td>

0.655188

.. raw:: html

   </td>

.. raw:: html

   <td>

0.701025

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

77122.950

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

82894.014

.. raw:: html

   </td>

.. raw:: html

   <td>

82894.014

.. raw:: html

   </td>

.. raw:: html

   <td>

24

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0188

.. raw:: html

   </td>

.. raw:: html

   <td>

490180

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0188

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.084215

.. raw:: html

   </td>

.. raw:: html

   <td>

0.010523

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-25 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.497690

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.068474

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.952786

.. raw:: html

   </td>

.. raw:: html

   <td>

0.031148

.. raw:: html

   </td>

.. raw:: html

   <td>

0.644272

.. raw:: html

   </td>

.. raw:: html

   <td>

0.704251

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

78697.050

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

77122.950

.. raw:: html

   </td>

.. raw:: html

   <td>

77122.950

.. raw:: html

   </td>

.. raw:: html

   <td>

25

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0193

.. raw:: html

   </td>

.. raw:: html

   <td>

90862

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0193

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.068474

.. raw:: html

   </td>

.. raw:: html

   <td>

0.031148

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-26 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.489730

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.084215

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.943240

.. raw:: html

   </td>

.. raw:: html

   <td>

0.010523

.. raw:: html

   </td>

.. raw:: html

   <td>

0.634965

.. raw:: html

   </td>

.. raw:: html

   <td>

0.703738

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

77122.950

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

78697.050

.. raw:: html

   </td>

.. raw:: html

   <td>

78697.050

.. raw:: html

   </td>

.. raw:: html

   <td>

26

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0201

.. raw:: html

   </td>

.. raw:: html

   <td>

2299

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0201

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.084215

.. raw:: html

   </td>

.. raw:: html

   <td>

0.010523

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-27 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.495916

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.049785

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.857592

.. raw:: html

   </td>

.. raw:: html

   <td>

0.055636

.. raw:: html

   </td>

.. raw:: html

   <td>

0.636644

.. raw:: html

   </td>

.. raw:: html

   <td>

0.713671

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

80565.936

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

77122.950

.. raw:: html

   </td>

.. raw:: html

   <td>

77122.950

.. raw:: html

   </td>

.. raw:: html

   <td>

27

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0195

.. raw:: html

   </td>

.. raw:: html

   <td>

663

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0195

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.049785

.. raw:: html

   </td>

.. raw:: html

   <td>

0.055636

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-28 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.488469

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.064490

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.848769

.. raw:: html

   </td>

.. raw:: html

   <td>

0.036368

.. raw:: html

   </td>

.. raw:: html

   <td>

0.627920

.. raw:: html

   </td>

.. raw:: html

   <td>

0.713212

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

79095.504

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

80565.936

.. raw:: html

   </td>

.. raw:: html

   <td>

80565.936

.. raw:: html

   </td>

.. raw:: html

   <td>

28

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0195

.. raw:: html

   </td>

.. raw:: html

   <td>

7061

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0195

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.064490

.. raw:: html

   </td>

.. raw:: html

   <td>

0.036368

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-29 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.479671

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.066903

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.822844

.. raw:: html

   </td>

.. raw:: html

   <td>

0.033205

.. raw:: html

   </td>

.. raw:: html

   <td>

0.616787

.. raw:: html

   </td>

.. raw:: html

   <td>

0.712868

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

78854.142

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

79095.504

.. raw:: html

   </td>

.. raw:: html

   <td>

79095.504

.. raw:: html

   </td>

.. raw:: html

   <td>

29

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0195

.. raw:: html

   </td>

.. raw:: html

   <td>

8526

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0195

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.066903

.. raw:: html

   </td>

.. raw:: html

   <td>

0.033205

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-30 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.476306

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.046605

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.769239

.. raw:: html

   </td>

.. raw:: html

   <td>

0.059803

.. raw:: html

   </td>

.. raw:: html

   <td>

0.610002

.. raw:: html

   </td>

.. raw:: html

   <td>

0.716464

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

80883.936

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

78854.142

.. raw:: html

   </td>

.. raw:: html

   <td>

78854.142

.. raw:: html

   </td>

.. raw:: html

   <td>

30

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0196

.. raw:: html

   </td>

.. raw:: html

   <td>

29654

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0196

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.046605

.. raw:: html

   </td>

.. raw:: html

   <td>

0.059803

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

…

.. raw:: html

   </th>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-05-30 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.495432

.. raw:: html

   </td>

.. raw:: html

   <td>

5.949752

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.016611

.. raw:: html

   </td>

.. raw:: html

   <td>

7.916664

.. raw:: html

   </td>

.. raw:: html

   <td>

0.554369

.. raw:: html

   </td>

.. raw:: html

   <td>

0.888883

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

680519.682

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

701826.000

.. raw:: html

   </td>

.. raw:: html

   <td>

701826.000

.. raw:: html

   </td>

.. raw:: html

   <td>

822

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

40157964723

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

5.949752

.. raw:: html

   </td>

.. raw:: html

   <td>

7.916664

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-05-31 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.495243

.. raw:: html

   </td>

.. raw:: html

   <td>

6.102328

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.017086

.. raw:: html

   </td>

.. raw:: html

   <td>

8.154164

.. raw:: html

   </td>

.. raw:: html

   <td>

0.554182

.. raw:: html

   </td>

.. raw:: html

   <td>

0.888844

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

695777.322

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

680519.682

.. raw:: html

   </td>

.. raw:: html

   <td>

680519.682

.. raw:: html

   </td>

.. raw:: html

   <td>

823

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

31098652109

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

6.102328

.. raw:: html

   </td>

.. raw:: html

   <td>

8.154164

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-01 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.495836

.. raw:: html

   </td>

.. raw:: html

   <td>

6.504967

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.014668

.. raw:: html

   </td>

.. raw:: html

   <td>

8.644144

.. raw:: html

   </td>

.. raw:: html

   <td>

0.554541

.. raw:: html

   </td>

.. raw:: html

   <td>

0.889303

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

736041.210

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

695777.322

.. raw:: html

   </td>

.. raw:: html

   <td>

695777.322

.. raw:: html

   </td>

.. raw:: html

   <td>

824

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

40944880757

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

6.504967

.. raw:: html

   </td>

.. raw:: html

   <td>

8.644144

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-02 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.495948

.. raw:: html

   </td>

.. raw:: html

   <td>

6.801995

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.013641

.. raw:: html

   </td>

.. raw:: html

   <td>

9.033331

.. raw:: html

   </td>

.. raw:: html

   <td>

0.554581

.. raw:: html

   </td>

.. raw:: html

   <td>

0.889440

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

765744.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

736041.210

.. raw:: html

   </td>

.. raw:: html

   <td>

736041.210

.. raw:: html

   </td>

.. raw:: html

   <td>

825

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

22364557424

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

6.801995

.. raw:: html

   </td>

.. raw:: html

   <td>

9.033331

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-03 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.495729

.. raw:: html

   </td>

.. raw:: html

   <td>

6.952409

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.013100

.. raw:: html

   </td>

.. raw:: html

   <td>

9.230418

.. raw:: html

   </td>

.. raw:: html

   <td>

0.554317

.. raw:: html

   </td>

.. raw:: html

   <td>

0.889470

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

780785.400

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

765744.000

.. raw:: html

   </td>

.. raw:: html

   <td>

765744.000

.. raw:: html

   </td>

.. raw:: html

   <td>

826

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

23687278961

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

6.952409

.. raw:: html

   </td>

.. raw:: html

   <td>

9.230418

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-04 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.495450

.. raw:: html

   </td>

.. raw:: html

   <td>

7.042244

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.012768

.. raw:: html

   </td>

.. raw:: html

   <td>

9.348122

.. raw:: html

   </td>

.. raw:: html

   <td>

0.553999

.. raw:: html

   </td>

.. raw:: html

   <td>

0.889479

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

789768.900

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

780785.400

.. raw:: html

   </td>

.. raw:: html

   <td>

780785.400

.. raw:: html

   </td>

.. raw:: html

   <td>

827

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

21332021248

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

7.042244

.. raw:: html

   </td>

.. raw:: html

   <td>

9.348122

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-05 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.496148

.. raw:: html

   </td>

.. raw:: html

   <td>

7.524987

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.011320

.. raw:: html

   </td>

.. raw:: html

   <td>

9.980649

.. raw:: html

   </td>

.. raw:: html

   <td>

0.554578

.. raw:: html

   </td>

.. raw:: html

   <td>

0.889805

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

838043.208

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

789768.900

.. raw:: html

   </td>

.. raw:: html

   <td>

789768.900

.. raw:: html

   </td>

.. raw:: html

   <td>

828

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0218

.. raw:: html

   </td>

.. raw:: html

   <td>

22372229837

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0218

.. raw:: html

   </td>

.. raw:: html

   <td>

7.524987

.. raw:: html

   </td>

.. raw:: html

   <td>

9.980649

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-06 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.497592

.. raw:: html

   </td>

.. raw:: html

   <td>

8.194835

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.009554

.. raw:: html

   </td>

.. raw:: html

   <td>

10.858330

.. raw:: html

   </td>

.. raw:: html

   <td>

0.555841

.. raw:: html

   </td>

.. raw:: html

   <td>

0.890368

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

905028.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

838043.208

.. raw:: html

   </td>

.. raw:: html

   <td>

838043.208

.. raw:: html

   </td>

.. raw:: html

   <td>

829

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0214

.. raw:: html

   </td>

.. raw:: html

   <td>

81923184446

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0214

.. raw:: html

   </td>

.. raw:: html

   <td>

8.194835

.. raw:: html

   </td>

.. raw:: html

   <td>

10.858330

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-07 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.498895

.. raw:: html

   </td>

.. raw:: html

   <td>

7.557258

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.011975

.. raw:: html

   </td>

.. raw:: html

   <td>

10.022932

.. raw:: html

   </td>

.. raw:: html

   <td>

0.557003

.. raw:: html

   </td>

.. raw:: html

   <td>

0.890845

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

841270.272

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

905028.000

.. raw:: html

   </td>

.. raw:: html

   <td>

905028.000

.. raw:: html

   </td>

.. raw:: html

   <td>

830

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0218

.. raw:: html

   </td>

.. raw:: html

   <td>

49070430356

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0218

.. raw:: html

   </td>

.. raw:: html

   <td>

7.557258

.. raw:: html

   </td>

.. raw:: html

   <td>

10.022932

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-08 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.499349

.. raw:: html

   </td>

.. raw:: html

   <td>

8.010395

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.010676

.. raw:: html

   </td>

.. raw:: html

   <td>

10.616664

.. raw:: html

   </td>

.. raw:: html

   <td>

0.557357

.. raw:: html

   </td>

.. raw:: html

   <td>

0.891092

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

886584.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

841270.272

.. raw:: html

   </td>

.. raw:: html

   <td>

841270.272

.. raw:: html

   </td>

.. raw:: html

   <td>

831

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0219

.. raw:: html

   </td>

.. raw:: html

   <td>

34013412940

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0219

.. raw:: html

   </td>

.. raw:: html

   <td>

8.010395

.. raw:: html

   </td>

.. raw:: html

   <td>

10.616664

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-09 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.499063

.. raw:: html

   </td>

.. raw:: html

   <td>

8.099750

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.010386

.. raw:: html

   </td>

.. raw:: html

   <td>

10.733746

.. raw:: html

   </td>

.. raw:: html

   <td>

0.557033

.. raw:: html

   </td>

.. raw:: html

   <td>

0.891098

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

895519.482

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

886584.000

.. raw:: html

   </td>

.. raw:: html

   <td>

886584.000

.. raw:: html

   </td>

.. raw:: html

   <td>

832

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

25275425996

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

8.099750

.. raw:: html

   </td>

.. raw:: html

   <td>

10.733746

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-10 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.498769

.. raw:: html

   </td>

.. raw:: html

   <td>

8.086143

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.010416

.. raw:: html

   </td>

.. raw:: html

   <td>

10.715915

.. raw:: html

   </td>

.. raw:: html

   <td>

0.556705

.. raw:: html

   </td>

.. raw:: html

   <td>

0.891098

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

894158.760

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

895519.482

.. raw:: html

   </td>

.. raw:: html

   <td>

895519.482

.. raw:: html

   </td>

.. raw:: html

   <td>

833

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

30620792046

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

8.086143

.. raw:: html

   </td>

.. raw:: html

   <td>

10.715915

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-11 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.498971

.. raw:: html

   </td>

.. raw:: html

   <td>

8.484533

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.009305

.. raw:: html

   </td>

.. raw:: html

   <td>

11.237914

.. raw:: html

   </td>

.. raw:: html

   <td>

0.556827

.. raw:: html

   </td>

.. raw:: html

   <td>

0.891266

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

933997.800

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

894158.760

.. raw:: html

   </td>

.. raw:: html

   <td>

894158.760

.. raw:: html

   </td>

.. raw:: html

   <td>

834

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

30830678595

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

8.484533

.. raw:: html

   </td>

.. raw:: html

   <td>

11.237914

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-12 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.503448

.. raw:: html

   </td>

.. raw:: html

   <td>

7.320494

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.014065

.. raw:: html

   </td>

.. raw:: html

   <td>

9.712706

.. raw:: html

   </td>

.. raw:: html

   <td>

0.560936

.. raw:: html

   </td>

.. raw:: html

   <td>

0.892695

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

817593.900

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

933997.800

.. raw:: html

   </td>

.. raw:: html

   <td>

933997.800

.. raw:: html

   </td>

.. raw:: html

   <td>

835

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

88704710635

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

7.320494

.. raw:: html

   </td>

.. raw:: html

   <td>

9.712706

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-13 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.503565

.. raw:: html

   </td>

.. raw:: html

   <td>

7.656697

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.013054

.. raw:: html

   </td>

.. raw:: html

   <td>

10.153225

.. raw:: html

   </td>

.. raw:: html

   <td>

0.560981

.. raw:: html

   </td>

.. raw:: html

   <td>

0.892830

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

851214.132

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

817593.900

.. raw:: html

   </td>

.. raw:: html

   <td>

817593.900

.. raw:: html

   </td>

.. raw:: html

   <td>

836

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

42251296767

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

7.656697

.. raw:: html

   </td>

.. raw:: html

   <td>

10.153225

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-14 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.506845

.. raw:: html

   </td>

.. raw:: html

   <td>

6.734516

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.016873

.. raw:: html

   </td>

.. raw:: html

   <td>

8.944917

.. raw:: html

   </td>

.. raw:: html

   <td>

0.563995

.. raw:: html

   </td>

.. raw:: html

   <td>

0.893862

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

758996.040

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

851214.132

.. raw:: html

   </td>

.. raw:: html

   <td>

851214.132

.. raw:: html

   </td>

.. raw:: html

   <td>

837

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

63183088135

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

6.734516

.. raw:: html

   </td>

.. raw:: html

   <td>

8.944917

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-15 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.506562

.. raw:: html

   </td>

.. raw:: html

   <td>

6.695367

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.016991

.. raw:: html

   </td>

.. raw:: html

   <td>

8.893622

.. raw:: html

   </td>

.. raw:: html

   <td>

0.563678

.. raw:: html

   </td>

.. raw:: html

   <td>

0.893865

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

755081.142

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

758996.040

.. raw:: html

   </td>

.. raw:: html

   <td>

758996.040

.. raw:: html

   </td>

.. raw:: html

   <td>

838

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

104677533974

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

6.695367

.. raw:: html

   </td>

.. raw:: html

   <td>

8.893622

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-16 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.506404

.. raw:: html

   </td>

.. raw:: html

   <td>

6.887855

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.016343

.. raw:: html

   </td>

.. raw:: html

   <td>

9.145831

.. raw:: html

   </td>

.. raw:: html

   <td>

0.563472

.. raw:: html

   </td>

.. raw:: html

   <td>

0.893913

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

774330.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

755081.142

.. raw:: html

   </td>

.. raw:: html

   <td>

755081.142

.. raw:: html

   </td>

.. raw:: html

   <td>

839

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

43479966625

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

6.887855

.. raw:: html

   </td>

.. raw:: html

   <td>

9.145831

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-17 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.507407

.. raw:: html

   </td>

.. raw:: html

   <td>

7.435283

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.014812

.. raw:: html

   </td>

.. raw:: html

   <td>

9.863113

.. raw:: html

   </td>

.. raw:: html

   <td>

0.564341

.. raw:: html

   </td>

.. raw:: html

   <td>

0.894311

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

829072.746

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

774330.000

.. raw:: html

   </td>

.. raw:: html

   <td>

774330.000

.. raw:: html

   </td>

.. raw:: html

   <td>

840

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

36800919715

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

7.435283

.. raw:: html

   </td>

.. raw:: html

   <td>

9.863113

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-18 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.507740

.. raw:: html

   </td>

.. raw:: html

   <td>

7.070069

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.016112

.. raw:: html

   </td>

.. raw:: html

   <td>

9.384581

.. raw:: html

   </td>

.. raw:: html

   <td>

0.564605

.. raw:: html

   </td>

.. raw:: html

   <td>

0.894482

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

792551.400

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

829072.746

.. raw:: html

   </td>

.. raw:: html

   <td>

829072.746

.. raw:: html

   </td>

.. raw:: html

   <td>

841

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

46411759478

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

7.070069

.. raw:: html

   </td>

.. raw:: html

   <td>

9.384581

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-19 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.507754

.. raw:: html

   </td>

.. raw:: html

   <td>

7.358645

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.015226

.. raw:: html

   </td>

.. raw:: html

   <td>

9.762694

.. raw:: html

   </td>

.. raw:: html

   <td>

0.564557

.. raw:: html

   </td>

.. raw:: html

   <td>

0.894583

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

821408.946

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

792551.400

.. raw:: html

   </td>

.. raw:: html

   <td>

792551.400

.. raw:: html

   </td>

.. raw:: html

   <td>

842

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0219

.. raw:: html

   </td>

.. raw:: html

   <td>

28294406623

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0219

.. raw:: html

   </td>

.. raw:: html

   <td>

7.358645

.. raw:: html

   </td>

.. raw:: html

   <td>

9.762694

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-20 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.507705

.. raw:: html

   </td>

.. raw:: html

   <td>

7.628795

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.014414

.. raw:: html

   </td>

.. raw:: html

   <td>

10.116664

.. raw:: html

   </td>

.. raw:: html

   <td>

0.564451

.. raw:: html

   </td>

.. raw:: html

   <td>

0.894665

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

848424.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

821408.946

.. raw:: html

   </td>

.. raw:: html

   <td>

821408.946

.. raw:: html

   </td>

.. raw:: html

   <td>

843

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

36903854052

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

7.628795

.. raw:: html

   </td>

.. raw:: html

   <td>

10.116664

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-21 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.507531

.. raw:: html

   </td>

.. raw:: html

   <td>

7.476155

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.014900

.. raw:: html

   </td>

.. raw:: html

   <td>

9.916664

.. raw:: html

   </td>

.. raw:: html

   <td>

0.564238

.. raw:: html

   </td>

.. raw:: html

   <td>

0.894696

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

833160.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

848424.000

.. raw:: html

   </td>

.. raw:: html

   <td>

848424.000

.. raw:: html

   </td>

.. raw:: html

   <td>

844

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

43815656010

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0216

.. raw:: html

   </td>

.. raw:: html

   <td>

7.476155

.. raw:: html

   </td>

.. raw:: html

   <td>

9.916664

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-22 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.507315

.. raw:: html

   </td>

.. raw:: html

   <td>

7.645891

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.014372

.. raw:: html

   </td>

.. raw:: html

   <td>

10.139065

.. raw:: html

   </td>

.. raw:: html

   <td>

0.563979

.. raw:: html

   </td>

.. raw:: html

   <td>

0.894725

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

850133.568

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

833160.000

.. raw:: html

   </td>

.. raw:: html

   <td>

833160.000

.. raw:: html

   </td>

.. raw:: html

   <td>

845

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

22304647568

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

7.645891

.. raw:: html

   </td>

.. raw:: html

   <td>

10.139065

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-23 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.507020

.. raw:: html

   </td>

.. raw:: html

   <td>

7.635155

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.014388

.. raw:: html

   </td>

.. raw:: html

   <td>

10.124997

.. raw:: html

   </td>

.. raw:: html

   <td>

0.563652

.. raw:: html

   </td>

.. raw:: html

   <td>

0.894725

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

849060.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

850133.568

.. raw:: html

   </td>

.. raw:: html

   <td>

850133.568

.. raw:: html

   </td>

.. raw:: html

   <td>

846

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

13090231864

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

7.635155

.. raw:: html

   </td>

.. raw:: html

   <td>

10.124997

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-24 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.507936

.. raw:: html

   </td>

.. raw:: html

   <td>

7.105628

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.016304

.. raw:: html

   </td>

.. raw:: html

   <td>

9.431173

.. raw:: html

   </td>

.. raw:: html

   <td>

0.564463

.. raw:: html

   </td>

.. raw:: html

   <td>

0.895061

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

796107.276

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

849060.000

.. raw:: html

   </td>

.. raw:: html

   <td>

849060.000

.. raw:: html

   </td>

.. raw:: html

   <td>

847

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

34088563732

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

7.105628

.. raw:: html

   </td>

.. raw:: html

   <td>

9.431173

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-25 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.507675

.. raw:: html

   </td>

.. raw:: html

   <td>

7.036714

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.016515

.. raw:: html

   </td>

.. raw:: html

   <td>

9.340880

.. raw:: html

   </td>

.. raw:: html

   <td>

0.564168

.. raw:: html

   </td>

.. raw:: html

   <td>

0.895069

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

789215.898

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

796107.276

.. raw:: html

   </td>

.. raw:: html

   <td>

796107.276

.. raw:: html

   </td>

.. raw:: html

   <td>

848

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

41560204433

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0215

.. raw:: html

   </td>

.. raw:: html

   <td>

7.036714

.. raw:: html

   </td>

.. raw:: html

   <td>

9.340880

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-26 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.507780

.. raw:: html

   </td>

.. raw:: html

   <td>

6.761571

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.017485

.. raw:: html

   </td>

.. raw:: html

   <td>

8.980368

.. raw:: html

   </td>

.. raw:: html

   <td>

0.564221

.. raw:: html

   </td>

.. raw:: html

   <td>

0.895175

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

761701.584

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

789215.898

.. raw:: html

   </td>

.. raw:: html

   <td>

789215.898

.. raw:: html

   </td>

.. raw:: html

   <td>

849

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0214

.. raw:: html

   </td>

.. raw:: html

   <td>

73840480752

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0214

.. raw:: html

   </td>

.. raw:: html

   <td>

6.761571

.. raw:: html

   </td>

.. raw:: html

   <td>

8.980368

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-27 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.508048

.. raw:: html

   </td>

.. raw:: html

   <td>

7.126355

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.016390

.. raw:: html

   </td>

.. raw:: html

   <td>

9.458331

.. raw:: html

   </td>

.. raw:: html

   <td>

0.564409

.. raw:: html

   </td>

.. raw:: html

   <td>

0.895349

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

798180.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

761701.584

.. raw:: html

   </td>

.. raw:: html

   <td>

761701.584

.. raw:: html

   </td>

.. raw:: html

   <td>

850

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

62426319778

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0221

.. raw:: html

   </td>

.. raw:: html

   <td>

7.126355

.. raw:: html

   </td>

.. raw:: html

   <td>

9.458331

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2017-06-28 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.507750

.. raw:: html

   </td>

.. raw:: html

   <td>

7.135895

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.016340

.. raw:: html

   </td>

.. raw:: html

   <td>

9.470831

.. raw:: html

   </td>

.. raw:: html

   <td>

0.564078

.. raw:: html

   </td>

.. raw:: html

   <td>

0.895349

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

799134.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

798180.000

.. raw:: html

   </td>

.. raw:: html

   <td>

798180.000

.. raw:: html

   </td>

.. raw:: html

   <td>

851

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0222

.. raw:: html

   </td>

.. raw:: html

   <td>

39676839183

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0222

.. raw:: html

   </td>

.. raw:: html

   <td>

7.135895

.. raw:: html

   </td>

.. raw:: html

   <td>

9.470831

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   </tbody>

.. raw:: html

   </table>

.. raw:: html

   <p>

851 rows × 45 columns

.. raw:: html

   </p>

.. raw:: html

   </div>

Also, instead of defining an output file we are accessing it via the “_"
variable that will be created in the name space and contain the
performance DataFrame.

.. code:: python

    _.head()

.. raw:: html

   <div>

.. raw:: html

   <table border="1" class="dataframe">

.. raw:: html

   <thead>

.. raw:: html

   <tr style="text-align: right;">

.. raw:: html

   <th>

.. raw:: html

   </th>

.. raw:: html

   <th>

algo_volatility

.. raw:: html

   </th>

.. raw:: html

   <th>

algorithm_period_return

.. raw:: html

   </th>

.. raw:: html

   <th>

alpha

.. raw:: html

   </th>

.. raw:: html

   <th>

benchmark_period_return

.. raw:: html

   </th>

.. raw:: html

   <th>

benchmark_volatility

.. raw:: html

   </th>

.. raw:: html

   <th>

beta

.. raw:: html

   </th>

.. raw:: html

   <th>

capital_used

.. raw:: html

   </th>

.. raw:: html

   <th>

cash

.. raw:: html

   </th>

.. raw:: html

   <th>

ending_cash

.. raw:: html

   </th>

.. raw:: html

   <th>

ending_exposure

.. raw:: html

   </th>

.. raw:: html

   <th>

…

.. raw:: html

   </th>

.. raw:: html

   <th>

starting_cash

.. raw:: html

   </th>

.. raw:: html

   <th>

starting_exposure

.. raw:: html

   </th>

.. raw:: html

   <th>

starting_value

.. raw:: html

   </th>

.. raw:: html

   <th>

trading_days

.. raw:: html

   </th>

.. raw:: html

   <th>

transactions

.. raw:: html

   </th>

.. raw:: html

   <th>

treasury_period_return

.. raw:: html

   </th>

.. raw:: html

   <th>

volume

.. raw:: html

   </th>

.. raw:: html

   <th>

treasury

.. raw:: html

   </th>

.. raw:: html

   <th>

algorithm

.. raw:: html

   </th>

.. raw:: html

   <th>

benchmark

.. raw:: html

   </th>

.. raw:: html

   </tr>

.. raw:: html

   </thead>

.. raw:: html

   <tbody>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-01 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

NaN

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

NaN

.. raw:: html

   </td>

.. raw:: html

   <td>

0.045833

.. raw:: html

   </td>

.. raw:: html

   <td>

NaN

.. raw:: html

   </td>

.. raw:: html

   <td>

NaN

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000

.. raw:: html

   </td>

.. raw:: html

   <td>

1

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0200

.. raw:: html

   </td>

.. raw:: html

   <td>

317

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0200

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

0.045833

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-02 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.000278

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.000025

.. raw:: html

   </td>

.. raw:: html

   <td>

0.011045

.. raw:: html

   </td>

.. raw:: html

   <td>

0.120833

.. raw:: html

   </td>

.. raw:: html

   <td>

0.290503

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.000956

.. raw:: html

   </td>

.. raw:: html

   <td>

-85544.474955

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

85542.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000

.. raw:: html

   </td>

.. raw:: html

   <td>

2

.. raw:: html

   </td>

.. raw:: html

   <td>

[{u’commission’: None, u’amount’: 318, u’sid’:…

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0208

.. raw:: html

   </td>

.. raw:: html

   <td>

98063

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0208

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.000025

.. raw:: html

   </td>

.. raw:: html

   <td>

0.120833

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-03 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.051796

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.005688

.. raw:: html

   </td>

.. raw:: html

   <td>

-1.197544

.. raw:: html

   </td>

.. raw:: html

   <td>

0.113416

.. raw:: html

   </td>

.. raw:: html

   <td>

0.633538

.. raw:: html

   </td>

.. raw:: html

   <td>

0.077239

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

84975.642

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

85542.000

.. raw:: html

   </td>

.. raw:: html

   <td>

85542.000

.. raw:: html

   </td>

.. raw:: html

   <td>

3

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0212

.. raw:: html

   </td>

.. raw:: html

   <td>

442983

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0212

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.005688

.. raw:: html

   </td>

.. raw:: html

   <td>

0.113416

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-04 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.342118

.. raw:: html

   </td>

.. raw:: html

   <td>

0.034955

.. raw:: html

   </td>

.. raw:: html

   <td>

0.401861

.. raw:: html

   </td>

.. raw:: html

   <td>

0.166666

.. raw:: html

   </td>

.. raw:: html

   <td>

0.524400

.. raw:: html

   </td>

.. raw:: html

   <td>

0.181468

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

89040.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

84975.642

.. raw:: html

   </td>

.. raw:: html

   <td>

84975.642

.. raw:: html

   </td>

.. raw:: html

   <td>

4

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0212

.. raw:: html

   </td>

.. raw:: html

   <td>

245889

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0212

.. raw:: html

   </td>

.. raw:: html

   <td>

0.034955

.. raw:: html

   </td>

.. raw:: html

   <td>

0.166666

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   <tr>

.. raw:: html

   <th>

2015-03-05 23:59:00+00:00

.. raw:: html

   </th>

.. raw:: html

   <td>

0.637226

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.038185

.. raw:: html

   </td>

.. raw:: html

   <td>

-3.914003

.. raw:: html

   </td>

.. raw:: html

   <td>

0.070834

.. raw:: html

   </td>

.. raw:: html

   <td>

0.976896

.. raw:: html

   </td>

.. raw:: html

   <td>

0.550520

.. raw:: html

   </td>

.. raw:: html

   <td>

0.000000

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

14455.525045

.. raw:: html

   </td>

.. raw:: html

   <td>

81726.000

.. raw:: html

   </td>

.. raw:: html

   <td>

…

.. raw:: html

   </td>

.. raw:: html

   <td>

100000.0

.. raw:: html

   </td>

.. raw:: html

   <td>

89040.000

.. raw:: html

   </td>

.. raw:: html

   <td>

89040.000

.. raw:: html

   </td>

.. raw:: html

   <td>

5

.. raw:: html

   </td>

.. raw:: html

   <td>

[]

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0211

.. raw:: html

   </td>

.. raw:: html

   <td>

117440

.. raw:: html

   </td>

.. raw:: html

   <td>

0.0211

.. raw:: html

   </td>

.. raw:: html

   <td>

-0.038185

.. raw:: html

   </td>

.. raw:: html

   <td>

0.070834

.. raw:: html

   </td>

.. raw:: html

   </tr>

.. raw:: html

   </tbody>

.. raw:: html

   </table>

.. raw:: html

   <p>

5 rows × 45 columns

.. raw:: html

   </p>

.. raw:: html

   </div>


.. note::

   Currently, the quote currency of all trading pairs ordered by the algorithm
   must match the value of the ``quote_currency``.

PyCharm IDE
~~~~~~~~~~~

PyCharm is an Integrated Development Environment (IDE) used in computer 
programming, specifically for the Python language. It streamlines the continuous
development of Python code, and among other things includes a debugger that 
comes in handy to see the inner workings of Catalyst, and your trading 
algorithms.

Install
^^^^^^^
Install PyCharm from their `Website <https://www.jetbrains.com/pycharm/download/>`__.
There is a free and open-source **Community** version.

Setup
^^^^^

1. When creating a new project in PyCharm, right under where you specify the Location,
   click on **Project Interpreter** to display a drop down menu

2. Select **Existing interpreter**, click the gear box right next to it and 
   select 'add local'. Depending on your installation, select either 
   "*Virtual Environment*" or "*Conda Environment" and click the '...' button to
   navigate to your catalyst env and select the Python binary file: 
   ``bin/python`` for Linux/MacOS installations or 'python.exe' for Windows 
   installs (for example: 'C:\\Users\\user\\Anaconda2\\envs\\catalyst\\python.exe'). 
   Select OK. You may want to click on *Make available to all projects* for your
   future reference. Click OK again, and create your new environment using the
   set up of your virtual environment.

Alternatively, if you already have your project created, in Windows do:

1. File -> Default Settings -> Project Interpreter. Click the gear box next to 
   the project interpreter and select ‘add local’, and follow the steps from the
   second step above.

On MacOS:

1. PyCharm -> Preferences -> Settings -> Project:’NAME_OF_PROJECT’ -> 
   Project Interpreter. Click the gear box next to the project interpreter 
   and select ‘add local’, and follow the steps from the second step above.

You should now be able to run your project/scripts in PyCharm.

Next steps
~~~~~~~~~~

We hope that this tutorial gave you a little insight into the
architecture, API, and features of Catalyst. For your next step, check
out some of the other :doc:`example algorithms<example-algos>`.

Feel free to ask questions on the ``#catalyst_dev`` channel of our 
`Discord group <https://discord.gg/SJK32GY>`__ and report
problems on our `GitHub issue tracker <https://github.com/enigmampc/catalyst/issues>`__.
