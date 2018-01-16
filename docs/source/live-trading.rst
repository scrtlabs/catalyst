Live Trading
============
This document explains how to get started with live trading.

Supported Exchanges
^^^^^^^^^^^^^^^^^^^
Catalyst can trade against these exchanges:

- Bitfinex, id= ``bitfinex``
- Bittrex, id= ``bittrex``
- Poloniex, id= ``poloniex``

Authentication
^^^^^^^^^^^^^^
Most exchanges require token key/secret combination for authentication. By
convention, Catalyst uses an ``auth.json`` file to hold this data.

This example illustrates the convention using the *Bitfinex* exchange.
Here is how to generate key and secret values for the Bitfinex exchange:
https://docs.bitfinex.com/v1/docs/api-access. Most exchanges follow
a similar process.

The auth.json file:

.. code-block:: json

  {
    "name": "bitfinex",
    "key": "my-key",
    "secret": "my-secret"
  }


The file goes here: ``~/.catalyst/data/exchanges/bitfinex/auth.json``

Note that the `bitfinex` part in the directory above corresponds to the id of the Bitfinex
exchange as defined in the "Supported Exchanges" section above.
Attempting to run an algorithm where the targeted exchange is missing
its ``auth.json`` file will create the directory structure and create an empty
auth.json file, but will result in an error.

Currency Symbols
^^^^^^^^^^^^^^^^
Catalyst introduces a universal convention to reference
trading pairs and individual currencies. This
is required to ensure that the ``symbol()`` api predictably
returns the correct asset regardless of the targeted exchange.

Exchanges tend to use their own convention to represent currencies
(e.g. XBT and BTC both represent Bitcoin on different exchanges).
Trading pairs are also inconsistent. For example, Bitfinex
puts the market currency before the base currency without a
separator, Bittrex puts the base currency first and uses a dash
seperator.

Here is the Catalyst convention:

*[Market Currency]_[Base Currency]* all lowercase.

Currency symbols (e.g. btc, eth, ltc) follow the Bittrex convention.

Here are some examples:

.. code-block:: json

  # With Bitfinex
  bitcoin_usd_asset = symbol('btc_usd')
  ethereum_bitcoin_asset = symbol('eth_btc')

  # With Bittrex
  ethereum_bitcoin_asset = symbol('eth_btc')
  neo_ethereum_asset = symbol('neo_eth)

Note that the trading pairs are always referenced in the same manner.
However, not all trading pairs are available on all exchanges. An
error will occur if the specified trading pair is not trading
on the exchange. To check which currency pairs are available on each 
of the supported exchanges, see 
`Catalyst Market Coverage <https://www.enigma.co/catalyst/status>`_.

Trading an Algorithm
^^^^^^^^^^^^^^^^^^^^
There is no special convention to follow when writing an
algorithm for live trading. The same algorithm should work in
backtest and live execution mode without modification.

What differs are the arguments provided to the catalyst client or
`run_algorithm()` interface. Here is the same example in both interfaces:

.. code-block:: bash

  catalyst live -f my_algo_code -x bitfinex -c btc -n my_algo_name 

.. code-block:: python

  run_algorithm(
      initialize=initialize,
      handle_data=handle_data,
      analyze=analyze,
      exchange_name='bitfinex',
      live=True,
      algo_namespace='my_algo_name',
      base_currency='btc'
  )


Here is the breakdown of the new arguments:

- ``live``: Boolean flag which enables live trading.
- ``capital_base``: The amount of base_currency assigned to the strategy.
  It has to be lower or equal to the amount of base currency available for
  trading on the exchange. For illustration, order_target_percent(asset, 1)
  will order the capital_base amount specified here of the specified asset.
- ``exchange_name``: The name of the targeted exchange
  (supported values: *bitfinex*, *bittrex*).
- ``algo_namespace``: A arbitrary label assigned to your algorithm for
  data storage purposes.
- ``base_currency``: The base currency used to calculate the
  statistics of your algorithm. Currently, the base currency of all
  trading pairs of your algorithm must match this value.
- ``simulate_orders``: Enables the paper trading mode, in which orders are
  simulated in Catalyst instead of processed on the exchange.

Here is a complete algorithm for reference:
`Buy Low and Sell High <https://github.com/enigmampc/catalyst/blob/master/catalyst/examples/buy_low_sell_high_live.py>`_
