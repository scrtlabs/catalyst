Catalyst & Jupyter Notebook
===========================

(`This is actual Notebook <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/running_catalyst_in_jupyter_notebook.ipynb>`_ referenced in the text below)

The `Jupyter Notebook <https://jupyter.org/>`__ is a very powerful
browser-based interface to a Python interpreter. As it is already the
de-facto interface for most quantitative researchers, ``catalyst``
provides an easy way to run your algorithm inside the Notebook without
requiring you to use the CLI.

Install
^^^^^^^

In order to use Jupyter Notebook, you first have to install it inside your
environment. It's available as ``pip`` package, so regardless of how you 
installed Catalyst, go inside your catalyst environemnt and run:

.. code:: bash

    (catalyst)$ pip install jupyter

Once you have Jupyter Notebook installed, every time you want to use it run:

.. code:: bash

    (catalyst)$ jupyter notebook

A local server will launch, and will open a new window on your browser. That's
the interface through which you will interact with Jupyter Notebook.

Running Algorithms
^^^^^^^^^^^^^^^^^^

Before running your algorithms inside the Jupyter Notebook, remember to ingest
the data from the command line interface (CLI). In the example below, you would
need to run first:

.. code:: bash

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
                stop_price=price*0.9,
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
