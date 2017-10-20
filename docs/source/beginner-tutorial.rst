Catalyst Beginner Tutorial
--------------------------

Basics
~~~~~~

Catalyst is an open-source algorithmic trading simulator for crypto
assets written in Python.

The source can be found at: https://github.com/enigmampc/catalyst

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
:doc:`installation instructions <install>` if you haven't set up 
Catalyst yet.

Every ``catalyst`` algorithm consists of at least two functions you have to
define:

* ``initialize(context)``
* ``handle_data(context, data)``

Before the start of the algorithm, ``catalyst`` calls the
``initialize()`` function and passes in a ``context`` variable.
``context`` is a persistent namespace for you to store variables you
need to access from one algorithm iteration to the next.

After the algorithm has been initialized, ``catalyst`` calls the
``handle_data()`` function once for each event. At every call, it passes
the same ``context`` variable and an event-frame called ``data``
containing the current trading bar with open, high, low, and close
(OHLC) prices as well as volume for each crypto asset in your universe. 

.. For more information on these functions, see the `relevant part of the
.. Quantopian docs <https://www.quantopian.com/help#api-toplevel>`.

My first algorithm
~~~~~~~~~~~~~~~~~~

Lets take a look at a very simple algorithm from the ``examples``
directory, ``buy_btc.py``:

.. code-block:: python

   from catalyst.api import order, record, symbol


   def initialize(context):
       context.asset = symbol('btc_usd')


   def handle_data(context, data):
       order(context.asset, 1)
       record(btc = data.current(context.asset, 'price'))


As you can see, we first have to import some functions we would like to
use. All functions commonly used in your algorithm can be found in
``catalyst.api``. Here we are using :func:`~catalyst.api.order()` which takes two
arguments: a cryptoasset object, and a number specifying how many assets you would
like to order (if negative, :func:`~catalyst.api.order()` will sell/short
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

Running the algorithm
~~~~~~~~~~~~~~~~~~~~~

To can now test this algorithm on crypto data, ``catalyst`` provides three
interfaces: 

-  A command-line interface,
-  ``IPython Notebook`` magic, 
-  and :func:`~catalyst.run_algorithm`.

Ingesting data
^^^^^^^^^^^^^^

In previous versions of Catalyst you needed to manually ingest data before running
your algorithm to make it available at runtime. Starting with version 0.3, the
algorithm will automagically ingest the data it needs the first time that encounters 
a data request for data that it doesn't have.

Still, we believe it is important for you to have a high-level understanding
of how data is managed:

-  Pricing data is split and packaged into ``bundles``: chunks of data organized 
   as time series that are kept up to date daily on Enigma's servers. Catalyst 
   downloads the bundles that needs at any given time, and reconstructs the whole
   dataset in your hard drive.

-  Pricing data is provided in ``daily`` and ``minute`` resolution. Those are different
   bundle datasets, and are managed separately.

-  Bundles are exchange-specific, as the pricing data is specific to the trades that
   happen in each exchange. You can optionally specify which exchange you want pricing
   data from.

-  Catalyst keeps track of all the downloaded bundles, so that it only has to download
   them once, and will do incremental updates as needed.

-  When running in ``live trading`` mode, Catalyst will first look for historical 
   pricing data in the locally stored bundles. If there is anything missing, Catalyst will
   hit the exchange for the most recent data, and merge it with the local bundle to make
   it available for future iterations.

If you want to learn more, check out the :ref:`ingesting data <ingesting-data>` section
for more detail.

Command line interface
^^^^^^^^^^^^^^^^^^^^^^

After you installed Catalyst you should be able to execute the following
from your command line (e.g. ``cmd.exe`` on Windows, or the Terminal app
on OSX). Displaying here a simplified output for eductional purposes:

.. code-block:: bash

   $ catalyst --help

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

There are three main modes you can run on Catalyst. The first being ``ingest-exchange`` 
for data ingestion, which we have summarized in the previous section. The second 
is ``live`` to use your algorithm to trade live against a given exchange, and the 
third mode ``run`` is to backtest your algorithm before trading live with it.

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
algorithm (``-f``) as well as a parameter to specify which exchange to use. 
There are also arguments for the date range to run the algorithm over 
(``--start`` and ``--end``). Finally, you'll want to save the performance 
metrics of your algorithm so that you can analyze how it performed. This is 
done via the ``--output`` flag and will cause it to write the performance 
``DataFrame`` in the pickle Python file format. Note that you can also define 
a configuration file with these parameters that you can then conveniently pass 
to the ``-c`` option so that you don't have to supply the command line args 
all the time (see the .conf files in the examples directory).

Thus, to execute our algorithm from above and save the results to
``buy_btc_simple_out.pickle`` we would call ``catalyst run`` as follows:

.. code-block:: python

    catalyst run -f buy_btc_simple.py -x bitfinex --start 2016-1-1 --end 2016-9-29 -o buy_simple_btc_out.pickle


.. 
.. parsed-literal

..    AAPL
..    [2015-11-04 22:45:32.820166] INFO: Performance: Simulated 3521 trading days out of 3521.
..    [2015-11-04 22:45:32.820314] INFO: Performance: first open: 2000-01-03 14:31:00+00:00
..    [2015-11-04 22:45:32.820401] INFO: Performance: last close: 2013-12-31 21:00:00+00:00


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

Let's take a quick look at the performance ``DataFrame``. For this, we
use ``pandas`` from inside the IPython Notebook and print the first ten
rows. Note that ``catalyst`` makes heavy usage of 
`pandas <http://pandas.pydata.org/>`_, especially for data input and 
outputting so it's worth spending some time to learn it.

.. code-block:: python

    import pandas as pd
    perf = pd.read_pickle('buy_btc_simple_out.pickle') # read in perf DataFrame
    perf.head()

There is a row for each trading day, starting on the first day of our 
simulation Jan 1st, 2016. In the columns you can find various
information about the state of your algorithm. The very first column
``btc`` was placed there by the ``record()`` function mentioned earlier
and allows us to plot the price of bitcoin. For example, we could easily
examine now how our portfolio value changed over time compared to the
bitcoin price.

Our algorithm performance as assessed by the
``portfolio_value`` closely matches that of the bitcoin price. This
is not surprising as our algorithm only bought bitcoin every chance it got.


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
we need a new concept: History

``data.history()`` is a convenience function that keeps a rolling window of
data for you. The first argument is the number of bars you want to
collect, the second argument is the unit (either ``'1d'`` for ``'1m'``
but note that you need to have minute-level data for using ``1m``). This is
a function we use in the ``handle_data()`` section:

.. code-block:: python

    from catalyst.api import order, record, symbol

    def initialize(context):
       context.i = 0
       context.asset = symbol('btc_usd')

   def handle_data(context, data):
       # Skip first 300 days to get full windows
       context.i += 1
       if context.i < 300:
           return

       # Compute averages
       # data.history() has to be called with the same params
       # from above and returns a pandas dataframe.
       short_mavg = data.history(context.asset, 'price', bar_count=100, frequency="1d").mean()
       long_mavg = data.history(context.asset, 'price', bar_count=300, frequency="1d").mean()

       # Trading logic
       if short_mavg > long_mavg:
           # order_target orders as many shares as needed to
           # achieve the desired number of shares.
           order_target(context.asset, 100)
       elif short_mavg < long_mavg:
           order_target(context.asset, 0)

       # Save values for later inspection
       record(btc=data.current(context.asset, 'price'),
              short_mavg=short_mavg,
              long_mavg=long_mavg)


Conclusions
~~~~~~~~~~~

We hope that this tutorial gave you a little insight into the
architecture, API, and features of ``catalyst``. For next steps, check
out some of the
`examples <https://github.com/enigmampc/catalyst/tree/master/catalyst/examples>`__.
The natural next step would be too look into the 
`buy_and_hodl <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/buy_and_hodl.py>`_ 
example, which is a more elaborated and realistic version of the ``buy_btc_simple`` example presented in this tutorial.

Feel free to ask questions on the ``#catalyst_dev`` channel of our 
`Discord group <https://discord.gg/SJK32GY>`__ and report
problems on our `GitHub issue tracker <https://github.com/enigmampc/catalyst/issues>`__.
