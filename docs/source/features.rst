Features
========

This page describes the features that Catalyst provides in the current version,
and what is planned for future releases.

Current Functionality
~~~~~~~~~~~~~~~~~~~~~

* Backtesting and live-trading modes to run your trading algorithms, with a 
  seamless transition between the two.
* Paper trading simulates order in live-trading mode.
* Support for four exchanges: Binance, Bitfinex, Bittrex and Poloniex in both modes
  (backtesting and live-trading). Historical data for backtesting is provided 
  with daily resolution for all four exchanges, and minute resolution for
  Binance, Bitfinex and Poloniex. No minute-resolution data is currently available for
  Bittrex. Refer to 
  `Catalyst Market Coverage <https://www.enigma.co/catalyst/status>`_ for 
  details.
* Interface with over 90 exchanges available in live and paper trading modes.
* Granular commission models which closely simulates each exchange fee
  structure in backtesting and paper trading.
* Standardized naming convention for all asset pairs trading on any exchange in 
  the form ``{base_currency}_{quote_currency}``. See
  :ref:`naming`.
* Output of performance statistics based on Pandas DataFrames to integrate 
  nicely into the existing PyData ecosystem.
* Support for running multiple algorithms on the same exchange independently of
  one another. Catalyst performance tracker stores just enough data to allow 
  algorithms to run independently while still sharing critical data through 
  exchanges.
* Benchmark defaults to Bitcoin price (btc_usdt in Poloniex exchange) for the 
  purpose of comparing performance across trading algorithms. A custom benchmark
  can be specified through ``set_benchmark()`` (but see 
  `issue #86 <https://github.com/enigmampc/catalyst/issues/86>`_). 
* Support for MacOS, Linux and Windows installations.
* Support for Python2 and Python3.
.. Support for accessing multiple exchanges per algorithm, which opens the door
.. to cross-exchange arbitrage opportunities.

For additional details on the functionality added on recent releases, see the
:doc:`Release Notes<releases>`.

Upcoming features
~~~~~~~~~~~~~~~~~

* Additional datasets beyond pricing data (Q1 2018)
* API documentation (Q1 2018)
* Support for decentralized exchanges (Q1 2018)
* Support for data ingestion of community-contributed data sets (Q1 2018)
* Pipeline support (Q1 2018)
* Web UI (Q2 2018)


 .. _naming:

Naming Convention
~~~~~~~~~~~~~~~~~

Catalyst introduces a standardized naming convention for all asset pairs 
trading on any exchange in the following form:


    **{base_currency}_{quote_currency}**

Where {base_currency} is the asset to be traded using {quote_currency} as
the reference, both written in lowercase and separated with an underscore.

This standardization is needed to overcome the lack of consistency in the 
naming of assets across different exchanges, and making it easier to the user
to refer to the asset pairs that you want to trade.

Catalyst maintains a `Market Coverage Overview <https://www.enigma.co/catalyst/status>`_ 
where you can check the mapping between Catalyst naming pairs and that of each 
exchange. Catalyst will always expect in all its functions that you will refer to 
the asset pairs by using the Catalyst naming convention.

If at any point, you input the wrong name for an asset pair, you will get an error 
of that pair not found in the given exchange, and a list of pairs available on that exchange:

.. code-block:: bash

   $ catalyst ingest-exchange -x poloniex -i btc_usd

.. parsed-literal::

	Ingesting exchange bundle poloniex...
	Error traceback: /Volumes/Data/Users/victoris/Desktop/Enigma/user-install/catalyst-dev/catalyst/exchange/exchange.py (line 175)
	SymbolNotFoundOnExchange:  Symbol btc_usd not found on exchange Poloniex. 
	Choose from: ['rep_usdt', 'gno_btc', 'xvc_btc', 'pink_btc', 'sys_btc', 
	'emc2_btc', 'rads_btc', 'note_btc', 'maid_btc', 'bch_btc', 'gnt_btc', 
	'bcn_btc', 'rep_btc', 'bcy_btc', 'cvc_btc', 'nxt_xmr', 'zec_usdt', 
	'fct_btc', 'gas_btc', 'pot_btc', 'eth_usdt', 'btc_usdt', 'lbc_btc', 
	'dcr_btc', 'etc_usdt', 'omg_eth', 'amp_btc', 'xpm_btc', 'nxt_btc', 
	'vtc_btc', 'steem_eth', 'blk_xmr', 'pasc_btc', 'zec_xmr', 'grc_btc', 
	'nxc_btc', 'btcd_btc', 'ltc_btc', 'dash_btc', 'naut_btc', 'zec_eth', 
	'zec_btc', 'burst_btc', 'zrx_eth', 'bela_btc', 'steem_btc', 'etc_btc', 
	'eth_btc', 'huc_btc', 'strat_btc', 'lsk_btc', 'exp_btc', 'clam_btc', 
	'rep_eth', 'dash_xmr', 'cvc_eth', 'bch_usdt', 'zrx_btc', 'dash_usdt', 
	'blk_btc', 'xrp_btc', 'nxt_usdt', 'neos_btc', 'omg_btc', 'bts_btc', 
	'doge_btc', 'gnt_eth', 'sbd_btc', 'gno_eth', 'xcp_btc', 'ltc_usdt', 
	'btm_btc', 'xmr_usdt', 'lsk_eth', 'omni_btc', 'nav_btc', 'fldc_btc', 
	'ppc_btc', 'xbc_btc', 'dgb_btc', 'sc_btc', 'btcd_xmr', 'vrc_btc', 
	'ric_btc', 'str_btc', 'maid_xmr', 'xmr_btc', 'sjcx_btc', 'via_btc', 
	'xem_btc', 'nmc_btc', 'etc_eth', 'ltc_xmr', 'ardr_btc', 'gas_eth', 
	'flo_btc', 'xrp_usdt', 'game_btc', 'bch_eth', 'bcn_xmr', 'str_usdt']

In the example above, exchange Poloniex does not use USD, but uses instead the 
USDT cryptocurrency asset that is issued on the Bitcoin blockchain via the Omni
Layer Protocol. Each USDT unit is backed by a U.S Dollar held in the reserves of 
Tether Limited. USDT can be transferred, stored, and spent, just like bitcoins 
or any other cryptocurrency. Given its 1:1 mapping to the USD, is a viable alternative.

.. code-block:: bash

   $ catalyst ingest-exchange -x poloniex -i btc_usdt

.. parsed-literal::

	Ingesting exchange bundle poloniex...
	    [====================================]  Fetching poloniex daily candles: :  100%

