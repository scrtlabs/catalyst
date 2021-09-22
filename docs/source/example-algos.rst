|

Example Algorithms
==================

This section documents a number of example algorithms to complement the 
beginner tutorial, and show how other trading algorithms can be implemented 
using Catalyst.

Overview
~~~~~~~~

- :ref:`Buy BTC Simple<buy_btc_simple>`: The simplest algorithm that introduces
  the ``initialize()`` and ``handle_data()`` functions, and is used in the 
  :doc:`beginner tutorial<beginner-tutorial>` to show how to run catalyst 
  for the first time.

- :ref:`Buy and Hodl <buy_and_hodl>`: A very straightforward *buy and hold* that 
  makes one single buy at the very beginning. Introduces the notions of 
  ``cash``, management of outstanding ``orders``, and ``order_target_value`` 
  to place orders. It also introduces the ``analyze()`` function to visualize 
  the performance of our strategy using the external library ``matplotlib``.

- :ref:`Dual Moving Average Crossover<dual_moving_average>`: A classic momentum 
  strategy used in the second part of the 
  `beginner tutorial <beginner-tutorial.html#history>`_ to introduce the 
  ``data.history()`` function. It makes a heavy use of ``matplotlib`` library 
  in the ``analyze()`` function to chart the performance of the algorithm.

- :ref:`Mean Reversion Algorithm <mean_reversion>`: Another simple momentum 
  strategy that is used in our 
  `two-part video tutorial <videos.html#backtesting-a-strategy>`_ to show how 
  to get started in backtesting and live trading with Catalyst.

- :ref:`Simple Universe <simple_universe>`: This code provides the 'universe' 
  of available trading pairs on a given exchange on any given day. You can use 
  this code to dynamically select which currency pairs you want to trade each 
  day of your strategy. This example does not make any trades. 

- :ref:`Portfolio Optimization <portfolio_optimization>`: Use this code to 
  execute a portfolio optimization model. This strategy will select the 
  portfolio with the maximum Sharpe Ratio. The parameters are set to use 180 
  days of historical data and rebalance every 30 days. This code was used in 
  writting the following article: 
  `Markowitz Portfolio Optimization for Cryptocurrencies <https://medium.com/catalyst-crypto/markowitz-portfolio-optimization-for-cryptocurrencies-in-catalyst-b23c38652556>`_.


.. _buy_btc_simple:

Buy BTC Simple Algorithm
~~~~~~~~~~~~~~~~~~~~~~~~

Source code: `examples/buy_btc_simple.py <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/buy_btc_simple.py>`_

.. literalinclude:: ../../catalyst/examples/buy_btc_simple.py
   :language: python

This simple algorithm does not produce any output nor displays any chart.


.. _buy_and_hodl:

Buy and Hodl Algorithm
~~~~~~~~~~~~~~~~~~~~~~

First ingest the historical pricing data needed to run this algorithm:

.. code-block:: bash

   catalyst ingest-exchange -x bitfinex -f daily -i btc_usd

Then, you can run the code below with the following command:

.. code-block:: bash

   catalyst run -f buy_and_hodl.py --start 2015-3-1 --end 2017-10-31 --capital-base 100000 -x bitfinex -c btc -o bah.pickle

or using the same parameters specified in the run_algorithm() function at the 
end of the file:

.. code-block:: bash

  python buy_and_hodl.py


This command will run the trading algorithm in the specified time range and 
plot the resulting performance using the matplotlib library. You can choose any 
date interval with the ``--start`` and ``--end`` parameters, but bear in mind 
that 2015-3-1 is the earliest date that Catalyst supports (if you choose an 
earlier date, you'll get an error), and the most recent date you can choose is 
one day prior to the current date. 

Source code: `examples/buy_and_hodl.py <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/buy_and_hodl.py>`_

.. literalinclude:: ../../catalyst/examples/buy_and_hodl.py
   :language: python

.. image:: https://s3.amazonaws.com/enigmaco-docs/github.io/example_buy_and_hodl.png

.. _dual_moving_average:

Dual Moving Average Crossover
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This strategy is covered in detail in the last part of 
`this tutorial <beginner-tutorial.html#history>`_.

Source Code: `examples/dual_moving_average.py <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/dual_moving_average.py>`_

.. literalinclude:: ../../catalyst/examples/dual_moving_average.py
   :language: python

.. image:: https://s3.amazonaws.com/enigmaco-docs/github.io/tutorial_dual_moving_average.png


.. _mean_reversion:

Mean Reversion Algorithm
~~~~~~~~~~~~~~~~~~~~~~~~

This algorithm is based on a simple momentum strategy. When the cryptoasset goes
up quickly, we're going to buy; when it goes down quickly, we're going to sell. 
Hopefully, we'll ride the waves.

We are choosing to backtest this trading algorithm with the ``neo_usd`` currency 
pairon the ``Bitfinex`` exchange. Thus, first ingest the historical pricing data
that we need, with minute resolution:

.. code-block:: bash

   catalyst ingest-exchange -x bitfinex -f minute -i neo_usd

To run this algorithm, we are opting for the Python interpreter, instead of the 
command line (CLI). All of the parameters for the simulation are specified in 
lines 218-245, so in order to run the algorithm we just type:

.. code-block:: bash

   python mean_reversion_simple.py

Source code: `examples/mean_reversion_simple.py <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/mean_reversion_simple.py>`_

.. literalinclude:: ../../catalyst/examples/mean_reversion_simple.py
   :language: python

.. image:: https://s3.amazonaws.com/enigmaco-docs/github.io/example_mean_reversion_simple.png

Notice the difference in performance between the charts above and those seen on 
`this video tutorial <https://youtu.be/PmwbYHjuyNQ>`_ at
minute 8:10. The buy and sell orders are triggered at the same exact times, but
the differences result from a more realistic slippage model 
implemented after the video was recorded, which executes the orders at slightly
different prices, but resulting in significant changes in performance of our 
strategy.

.. _simple_universe:

Simple Universe
~~~~~~~~~~~~~~~

This example aims to provide an easy way for users to learn how to 
collect data from any given exchange and select a subset of the available
currency pairs for trading. You simply need to specify the exchange and 
the market (quote_currency) that you want to focus on. You will then see
how to create a universe of assets, and filter it based on the market you
desire.

The example prints out the closing price of all the pairs for a given 
market in a given exchange every 30 minutes. The example also contains 
the OHLCV data with minute-resolution for the past seven days which 
could be used to create indicators. Use this code as the backbone to 
create your own trading strategy.

The lookback_date variable is used to ensure data for a coin existed on 
the lookback period specified.

To run, execute the following two commands in a terminal (inside catalyst 
environment). The first one retrieves all the pricing data needed for this
script to run (only needs to be run once), and the second one executes this
script with the parameters specified in the run_algorithm() call at the end 
of the file:

.. code-block:: bash
  
  catalyst ingest-exchange -x bitfinex -f minute

Source code: `examples/simple_universe.py <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/simple_universe.py>`_

.. literalinclude:: ../../catalyst/examples/simple_universe.py
   :language: python


.. _portfolio_optimization:

Portfolio Optimization
~~~~~~~~~~~~~~~~~~~~~~

Use this code to execute a portfolio optimization model. This strategy will 
select the portfolio with the maximum Sharpe Ratio. The parameters are set to 
use 180 days of historical data and rebalance every 30 days. This code was used 
in writting the following article: 
`Markowitz Portfolio Optimization for Cryptocurrencies <https://medium.com/catalyst-crypto/markowitz-portfolio-optimization-for-cryptocurrencies-in-catalyst-b23c38652556>`_.

Source code: `examples/portfolio_optimization.py <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/portfolio_optimization.py>`_

.. literalinclude:: ../../catalyst/examples/portfolio_optimization.py
   :language: python

.. image:: https://cdn-images-1.medium.com/max/1600/0*EjjiKZHlYF3sn7yQ.
   :align: center



