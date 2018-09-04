Utilities
=========

This section covers a variety of utilites that provide complimentary 
functionality to your trading algorithms. These are code snippets that you can
add to any algorithm to add the desired functionality.

If you are looking for example trading algorithms, see the corresponding section.

Output to CSV file
~~~~~~~~~~~~~~~~~~

Add this script to the analyze method to create and save a CSV file with the 
results from the trading algorithm. This file will include the default 
parameters of the results DataFrame plus any recorded variables and will be 
saved in the same location where your trading algorithm is saved. The exact 
script that you need to use depends on the interface that you are using to run 
your trading algorithm, which could be the CLI or a Python Interpreter.

1. Script to use with CLI:

.. code-block:: python

    def analyze(context=None, results=None):
        import sys
        import os
        from os.path import basename

        # Save results in CSV file
        filename = os.path.splitext(basename(sys.argv[3]))[0]
        results.to_csv(filename + '.csv')

2. Script to use with Python Interpreter:

.. code-block:: python

    def analyze(context=None, results=None):
        import os
        from os.path import basename

        # Save results in CSV file
        filename = os.path.splitext(os.path.basename(__file__))[0]
        results.to_csv(filename + '.csv')

Extracting market data
~~~~~~~~~~~~~~~~~~~~~~

Use this script to save the price and volume data of one cryptoasset in a CSV
file, which will be saved in the same location and with the same name as your
Python file. To get custom data, simply modify the asset's symbol and the dates.
Run this script directly from your development environment: python scriptname.py,
where the contents of 'scriptname.py' are as follows. Two different version are
provided as an example for daily- and minute-resolution data respectively:

Simpler case for daily data

.. code-block:: python

    import os
    import pytz
    from datetime import datetime

    from catalyst.api import record, symbol, symbols
    from catalyst.utils.run_algo import run_algorithm

    def initialize(context):
        # Portfolio assets list
        context.asset = symbol('btc_usdt') # Bitcoin on Poloniex

    def handle_data(context, data):
        # Variables to record for a given asset: price and volume
        price = data.current(context.asset, 'price')
        volume = data.current(context.asset, 'volume')
        record(price=price, volume=volume)

    def analyze(context=None, results=None):
        # Generate DataFrame with Price and Volume only
        data = results[['price','volume']]

        # Save results in CSV file
        filename = os.path.splitext(os.path.basename(__file__))[0]
        data.to_csv(filename + '.csv')

    ''' Bitcoin data is available on Poloniex since 2015-3-1.
         Dates vary for other tokens. In the example below, we choose the
         full month of July of 2017.
    '''
    start = datetime(2017, 1, 1, 0, 0, 0, 0, pytz.utc)
    end = datetime(2017, 7, 31, 0, 0, 0, 0, pytz.utc)
    results = run_algorithm(initialize=initialize,
                                    handle_data=handle_data,
                                    analyze=analyze,
                                    start=start,
                                    end=end,
                                    exchange_name='poloniex',
                                    capital_base=10000,
                                    quote_currency = 'usdt')

More versatile case for minute data

.. code-block:: python

    import os
    import csv
    import pytz
    from datetime import datetime

    from catalyst.api import record, symbol, symbols
    from catalyst.utils.run_algo import run_algorithm


    def initialize(context):
        # Portfolio assets list
        context.asset = symbol('btc_usdt') # Bitcoin on Poloniex

        # Create an empty DataFrame to store results
        context.pricing_data = pd.DataFrame()

    def handle_data(context, data):
        # Variables to record for a given asset: price and volume
        # Other options include 'open', 'high', 'open', 'close'
        # Please note that 'price' equals 'close'
        current = data.history(context.asset, ['price', 'volume'], 1, '1T')

        # Append the current information to the pricing_data DataFrame
        context.pricing_data = context.pricing_data.append(current)

    def analyze(context=None, results=None):
        # Save pricing data to a CSV file
        filename = os.path.splitext(os.path.basename(__file__))[0]
        context.pricing_data.to_csv(filename + '.csv')

    ''' Bitcoin data is available on Poloniex since 2015-3-1.
         Dates vary for other tokens.
    '''
    start = datetime(2017, 7, 30, 0, 0, 0, 0, pytz.utc)
    end = datetime(2017, 7, 31, 0, 0, 0, 0, pytz.utc)
    results = run_algorithm(initialize=initialize,
                            handle_data=handle_data,
                            analyze=analyze,
                            start=start,
                            end=end,
                            exchange_name='poloniex',
                            data_frequency='minute',
                            quote_currency ='usdt',
                            capital_base=10000 )