========
Catalyst
========

|version status|

Catalyst is an algorithmic trading library for crypto-assets written in Python.
It allows trading strategies to be easily expressed and backtested against historical data, providing analytics and insights regarding a particular strategy's performance.
Catalyst will be expanded to support live-trading of crypto-assets in the coming months.
Please visit `<enigma.co>`_ to learn about Catalyst, or refer to the 
`whitepaper <https://www.enigma.co/enigma_catalyst.pdf>`_ for further technical details.

Catalyst builds on top of the well-established `Zipline <https://github.com/quantopian/zipline>`_ project.
We did our best to minimize structural changes to the general API to maximize compatibility with existing trading algorithms, developer knowledge, and tutorials.
For now, please refer to the `Zipline API Docs <http://zipline.io>`_ as a general reference and bring any other questions you have to our #dev channel on `Slack <https://join.slack.com/enigmacatalyst/shared_invite/MTkzMjQ0MTg1NTczLTE0OTY3MjE3MDEtZGZmMTI5YzI3ZA>`_.

Our primary contributions include the:

- Intruction of an open trading calendar, that permits simulation to allow trades on weekends, holidays, and outside of normal business hours.
- Curation of OHLCV data bundle from `Poloniex's API <https://poloniex.com/support/api/>`_, which contains data in five-minute intervals as early as 2/19/2015.
- Support for backtesting for daily trading strategies, support for five-minute backtesting is in development.
- Addition Bitcoin price (USDT_BTC) as a benchmark asset for comparing performance.

Interested in getting involved?
`Join us on Slack! <https://join.slack.com/enigmacatalyst/shared_invite/MTkzMjQ0MTg1NTczLTE0OTY3MjE3MDEtZGZmMTI5YzI3ZA>`_


Installation
============

At the moment, Catalyst has some fairly specific and strict depedency requirements.
We recommend the use of Python virtual environments if you wish to simplify the installation process, or otherwise isolate Catalyst's dependencies from your other projects.
If you don't have ``virtualenv`` installed, see our later section on Virtual Environments.

.. code-block:: bash

    $ virtualenv catalyst-venv
    $ source ./catalyst-venv/bin/activate
    $ pip install enigma-catalyst

**Note:** A successful installation will require several minutes in order to compile dependencies that expose C APIs.

Dependencies
------------

Catalyst's depedencies can be found in the ``etc/requirements.txt`` file.
If you need to install them outside of a typical ``pip install``, this is done using:

.. code-block:: bash

    $ pip install -r etc/requirements.txt

Though not required by Catalyst directly, our example algorithms use matplotlib to visually display backtest results.
If you wish to run any examples or use matplotlib during development, it can be installed using:

.. code-block:: bash

    $ pip install matplotlib

**Note:** If you plan to use matplotlib and virtualenv on Mac OS X, see our later section for additional setup instructions.

Getting Started
===============

The following code implements a simple buy and hodl algorithm.  The full source can be found in ``catalyst/examples/buy_and_hodl.py``.

.. code:: python

    import numpy as np
    
    from catalyst.api import (
        order_target_value,
        symbol,
        record,
        cancel_order,
        get_open_orders,
    )
    
    ASSET = 'USDT_BTC'
    
    TARGET_HODL_RATIO = 0.8
    RESERVE_RATIO = 1.0 - TARGET_HODL_RATIO

    def initialize(context):
        context.is_buying = True
        context.asset = symbol(ASSET)

    def handle_data(context, data):
        cash = context.portfolio.cash
        target_hodl_value = TARGET_HODL_RATIO * context.portfolio.starting_cash
        reserve_value = RESERVE_RATIO * context.portfolio.starting_cash
        
        # Cancel any outstanding orders from the previous day
        orders = get_open_orders(context.asset) or []
        for order in orders:
            cancel_order(order)
        
        # Stop buying after passing reserve threshold
        if cash <= reserve_value:
            context.is_buying = False
        
        # Retrieve current price from pricing data
        price = data[context.asset].price
        
        # Check if still buying and could (approximately) afford another purchase                    
        if context.is_buying and cash > price:
            # Place order to make position in asset equal to target_hodl_value
            order_target_value(
                context.asset,
                target_hodl_value,
                limit_price=1.1 * price,
                stop_price=0.9 * price,
            )
        
        # Record any state for later analysis
        record(
            price=price,
            cash=context.portfolio.cash,
            leverage=context.account.leverage,
        )


You can then run this algorithm using the Catalyst CLI. From the command
line, run:

.. code:: bash

    $ catalyst ingest
    $ catalyst run -f buy_and_hodl.py --start 2015-3-1 --end 2017-6-28 --capital-base 100000 -o bah.pickle

This will download the crypto-asset price data from a poloniex bundle
curated by Enigma in the specified time range and stream it through
the algorithm and plot the resulting performance using matplotlib.

You can find other examples in the ``catalyst/examples`` directory.

Limitations
-----------

This project is currently in a pre-alpha state and has some limitations we'd like to address:

- *Minimum Denomination:* The smallest tradable unit in Catalyst is equal to 1/1000th of a full coin. We plan to enable more granular increments, but have capped it at 1/1000th for the time being.
- *Supported Assets:* Currently the poloniex bundle comes prepopulated with data for all 90 registered trading pairs. However, due to limitations in how portfolios are currently modeled, we recommend sticking to ``USDT_*`` trading pairs. USDT is an independent currency listed on Poloniex whose price is pegged to the US dollar. Currently, this list includes: ``USDT_BTC``, ``USDT_DASH``, ``USDT_ETC``, ``USDT_ETH``, ``USDT_LTC``, ``USDT_NXT``, ``USDT_REP``, ``USDT_STR``, ``USDT_XMR``, ``USDT_XRP``, and ``USDT_ZEC``. We plan to add support for basing your portfolio in arbitrary currencies and provide native support for modeling ForEx trades in the near future!

Virtual Environments
====================

Here we will provide a brief tutorial for installing ``virtualenv`` and its basic usage.
For more information regarding ``virtualenv``, please refer to this `virtualenv guide <http://python-guide-pt-br.readthedocs.io/en/latest/dev/virtualenvs/>`_.

The ``virtualenv`` command can be installed using:

.. code-block:: bash

    $ pip install virtualenv

To create a new virtual environment, choose a directory, e.g. ``/path/to/venv-dir``, where project-specific packages and files will be stored.  The environment is created by running:

.. code-block:: bash

    $ virtualenv /path/to/venv-dir

To enter an environment, run the ``bin/activate`` script located in ``/path/to/venv-dir`` using:

.. code-block:: bash

    $ source /path/to/venv-dir/bin/activate

Exiting an environment is accomplished using ``deactivate``, and removing it entirely is done by deleting ``/path/to/venv-dir``.

OS X + virtualenv + matplotlib
-------------------------------------

A note about using matplotlib in virtual enviroments on OS X: it may be necessary to run

.. code-block:: python

    echo "backend: TkAgg" > ~/.matplotlib/matplotlibrc

in order to override the default ``macosx`` backend for your system, which may not be accessible from inside the virtual environment.
This will allow Catalyst to open matplotlib charts from within a virtual environment, which is useful for displaying the performance of your backtests.  To learn more about matplotlib backends, please refer to the
`matplotlib backend documentation <https://matplotlib.org/faq/usage_faq.html#what-is-a-backend>`_.

Disclaimer
==========

Keep in mind that this project is still under active development, and is not recommended for production use in its current state.
We are deeply committed to improving the overall user experience, reliability, and feature-set offered by Catalyst.
If you have any suggestions, feedback, or general improvements regarding any of these topics, please let us know!

Hello World,

The Enigma Team

.. |version status| image:: https://img.shields.io/pypi/pyversions/enigma-catalyst.svg
   :target: https://pypi.python.org/pypi/enigma-catalyst
