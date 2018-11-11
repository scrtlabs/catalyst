=============
Release Notes
=============
Version 0.5.21
^^^^^^^^^^^^^^
**Release Date**: 2018-11-11

Build
~~~~~
- Upgraded the `redo` lib version :issue:`494`
- Added the ability to disable the alpha warning :issue:`493`
- Memoized the call to the `get_exchnage_folder()` function :issue:`500`
- Upgraded the `requests` lib

Version 0.5.20
^^^^^^^^^^^^^^
**Release Date**: 2018-09-13

Build
~~~~~
- Utilize the `trading_state` attribute of the `TradingPair` object - in live
  and paper trading ONLY :issue:`460`
- Introduced a first WIP version for running backtest strategies on a
  remote server

Version 0.5.19
^^^^^^^^^^^^^^
**Release Date**: 2018-09-04

Build
~~~~~
- Upgraded `CCXT` version to 1.17.94
- Added the `get_orderbook` function to the API.
- Aligned the `data.current` to crypto OHLCV left labeling.
- Added the support for live trading in Huobi Pro, OKEx, HitBTC and KuCoin.

Bug Fixes
~~~~~~~~~
- Fixed the timeout handling in `get_candles` function :issue:`420`
- Fixed the catalyst conda yml installation on windows :issue:`407`

Version 0.5.18
^^^^^^^^^^^^^^
**Release Date**: 2018-07-22

Build
~~~~~
- The parameter of the `set_slippage` API function was updated from spread to
  slippage to better describe its purpose in the fixed slippage model.

Version 0.5.17
^^^^^^^^^^^^^^
**Release Date**: 2018-07-19

Bug Fixes
~~~~~~~~~
- Reverted the start date of the trading clock to `2015-03-01`. This should be
  addressed after the entire data is acquired :issue:`408`

Version 0.5.16
^^^^^^^^^^^^^^
**Release Date**: 2018-07-19

Build
~~~~~
- Enabled the `get_orderbook` function in live and paper trading.
- Utilized unit tests and added travis CI integration.
- Updated the trading calender start date to `2013-04-01`.
- Terms and conditions were added to the marketplace.

Bug Fixes
~~~~~~~~~
- Fixed a bug in the filled order amount calculation at live mode :issue:`384`
- Fixed an issue with the order creation procedure for exchanges that do not
  support `fetchMyTrades` method :issue:`404`

Version 0.5.15
^^^^^^^^^^^^^^
**Release Date**: 2018-07-02

Build
~~~~~
- Add support for Binance historical data.

Bug Fixes
~~~~~~~~~
- Fixed a bug preventing ingestion from a csv if specifying an unsupported
  exchange.
- Fixed issues with installing catalyst using pip.

Version 0.5.14
^^^^^^^^^^^^^^
**Release Date**: 2018-06-21

Build
~~~~~
- Utilized `cancel_order` in paper mode and fixed minor issues in live mode
  :issue:`95`, :issue:`346`

Bug Fixes
~~~~~~~~~
- Added a retry mechanism to the handling of an order request timeout
  :issue:`350`, :issue:`356`
- Docker image file was utilized :issue:`366`
- Fixed the `ordered_pip` script used for the development environment
  installation :issue:`351`
- Fixed bugs in the `get_order` function :issue:`367` :issue:`372`
- Updated the observed portfolio balance :issue:`373`

Version 0.5.13
^^^^^^^^^^^^^^
**Release Date**: 2018-06-07

Build
~~~~~
- Added functions to marketplace client to get withdraw amount entitled to
  and to withdraw ENG as well.
- Updates to handle web3 upgrade on the marketplace.

Bug Fixes
~~~~~~~~~
- Pull request :issue:`334`.
- Raise error when trying to ingest non existing data.

Version 0.5.12
^^^^^^^^^^^^^^
**Release Date**: 2018-05-23

Build
~~~~~
- Renamed the `base_currency` parameter of run_algorithm to `quote_currency`
  for alignment with the Forex trading terminology.
- Improved the commissions calculations in live mode - documented at
  `Live trading <https://enigma.co/catalyst/live-trading.html#commissions>`_

Bug Fixes
~~~~~~~~~
- Fixed an issue preventing trading on Gdax with several positions
  :issue:`299`

Version 0.5.11
^^^^^^^^^^^^^^
**Release Date**: 2018-05-09

Bug Fixes
~~~~~~~~~
- Added missing start_date argument on live mode when running on cli
  :issue:`330`
- Updated the start and end arguments used on cli in live mode to include
  time information in addition to the date.

Version 0.5.10
^^^^^^^^^^^^^^
**Release Date**: 2018-05-09

Bug Fixes
~~~~~~~~~
- Added order creation exception handling according to the ccxt manual
  :issue:`315`
- Rounded up the filled amount to avoid unclosed orders :issue:`309`
- Correct the retry of the fetch trades method in case of a
  timeout :issue:`321`
- Fixed the extra history candles fetch in live mode :issue:`323`
- Fixed the marketplace list function :issue:`327`

Build
~~~~~
- Added the ability to set a future start_date on live mode :issue:`318`

Version 0.5.9
^^^^^^^^^^^^^
**Release Date**: 2018-04-24

Documentation
~~~~~~~~~~~~~
- Added explanation describing the storing of the algorithm state in live mode :issue:`224`
- Addition of
  `Api Reference <https://enigma.co/catalyst/appendix.html>`_

Bug Fixes
~~~~~~~~~
- Lowered order size limit to fit all supported exchanges :issue:`296`
- Added a graceful finish to a live run with a specified end date :issue:`302`
- Added commissions to `daily_stats` Dataframe :issue:`304`
- Fixed an issue regarding `str_btc` on Poloniex :issue:`307`
- Fixed the last candle returned in backtest in minute mode to be partial (as in live mode)
  :issue:`266`

Build
~~~~~
- Upgraded `CCXT` version to 1.12.131
- Updated Data Marketplace to enable submitting several files in a publish command.
- Improved Data Marketplace ingestion.

Version 0.5.8
^^^^^^^^^^^^^
**Release Date**: 2018-03-29

Bug Fixes
~~~~~~~~~
- Fix proper release of Data Marketplace on mainnet.
- Fix Data Marketplace release on mainnet

Version 0.5.7
^^^^^^^^^^^^^
**Release Date**: 2018-03-29

Build
~~~~~
- Data Marketplace deployed on mainnet.
- Added progress indicators for publishing data, and made the data publishing
  synchronous to provide feedback to the publisher.

Bug Fixes
~~~~~~~~~
- Fixes in storing and loading the state :issue:`214`,
  :issue:`287`

Version 0.5.6
^^^^^^^^^^^^^
**Release Date**: 2018-03-22

Build
~~~~~
- Data Marketplace: ensures compatibility across wallets, now fully supporting 
  ``ledger``, ``trezor``, ``keystore``, ``private key``. Partial support for 
  ``metamask`` (includes sign_msg, but not sign_tx). Current support for 
  ``Digital Bitbox`` is unknown, but believed to be supported.
- Data Marketplace: Switched online provider from MyEtherWallet to MyCrypto.
- Data Marketplace: Added progress indicator for data ingestion.

Bug Fixes
~~~~~~~~~
- Changed benchmark to be constant, so it doesn't ingest data at all. Temporary
  fix for :issue:`271`, :issue:`285`

Version 0.5.5
^^^^^^^^^^^^^
**Release Date**: 2018-03-19

Bug Fixes
~~~~~~~~~
- Fixed an issue with the data history in daily frequency :issue:`274`
- Fix hourly frequency issues :issue:`227` and :issue:`114`

Version 0.5.4
^^^^^^^^^^^^^
**Release Date**: 2018-03-14

Build
~~~~~
- Switched Data Marketplace from Ropstein testnet to Rinkeby testnet after 
  incorporating changes resulting from the marketplace contract audit
- Several usability improvements of the Data Marketplace that make the 
  `--dataset` parameter optional. If it is not included in the command line, 
  will list available datasets, and let you choose interactively.

Bug Fixes
~~~~~~~~~
- Fix Binance requirement of symbol to be included in the cancelled order 
  :issue:`204`
- Fix `notenoughcasherror` when an open order is filled minutes later 
  :issue:`237`
- Properly handle of empty candles received from exchanges :issue:`236`
- Added a function to reduce open orders amount from calculated target/amount 
  for target orders :issue:`243`
- Fix missing file in live trading mode on date change :issue:`252`, 
  :issue:`253`
- Upgraded Data Marketplace to Web3==4.0.0b11, which was breaking some 
  functionality from prior version 4.0.0b7 :issue:`257`
- Always request more data to avoid empty bars and always give the exact bar
  number :issue:`260`

Documentation
~~~~~~~~~~~~~
- PyCharm documentation :issue:`195`
- Added TA-Lib troubleshooting instructions
- Added instructions on how to create a Conda environment for Python 3.6, and
  updated Visual C++ instructions for Windows and Python 3
- Linking example algorithms in the documentation to their sources


Version 0.5.3
^^^^^^^^^^^^^
**Release Date**: 2018-02-09

Bug Fixes
~~~~~~~~~
- Fixed an issue with last candle in backtesting :issue:`219`

Version 0.5.2
^^^^^^^^^^^^^
**Release Date**: 2018-02-08

Bug Fixes
~~~~~~~~~
- Fixed an issue with live candle values :issue:`216` and :issue:`199`

Version 0.5.1
^^^^^^^^^^^^^
**Release Date**: 2018-02-07

Bug Fixes
~~~~~~~~~
- Fixed an issue with orders that stay open :issue:`211`
- Fixed Jupyter issues :issue:`179`
- Fetching multiple tickers in one call to minimize rate limit risks :issue:`174`
- Improved live state presentation :issue:`171`


Build
~~~~~
- Introducing the Enigma Marketplace

Version 0.4.7
^^^^^^^^^^^^^
**Release Date**: 2018-01-19

Bug Fixes
~~~~~~~~~
- Fixing issue :issue:`137` impacting the CLI

Build
~~~~~
- Implemented authentication aliases (:issue:`60`)

Version 0.4.6
^^^^^^^^^^^^^
**Release Date**: 2018-01-18

Bug Fixes
~~~~~~~~~
- Fixed some Python3 issues
- Reading the trade log to get executed order prices on exchanges like Binance (:issue:`151`)
- Fixed issue with market order executing price (:issue:`150` and :issue:`111`)
- Implemented standardized symbol mapping (:issue:`157`)
- Improved error handling for unsupported timeframes (:issue:`159`)
- Using Bitfinex instead of Poloniex to fetch btc_usdt benchmark (:issue:`161`)


Build
~~~~~
- Added a `context.state` dict to keep arbitrary state values between runs
- Added ability to stop live algo at specified end date

Version 0.4.5
^^^^^^^^^^^^^
**Release Date**: 2018-01-12

Bug Fixes
~~~~~~~~~
- Improved order execution for exchanges supporting trade lists (:issue:`151`)
- Fixed an issue where requesting history of multiple assets repeats values
- Raising an error for order amounts smaller than exchange lots
- Handling multiple req errors with tickers more gracefully (:issue:`160`)

Version 0.4.4
^^^^^^^^^^^^^
**Release Date**: 2018-01-09

Bug Fixes
~~~~~~~~~
- Removed redundant capital_base validation (:issue:`142`)
- Fixed portfolio update issue with restored state (:issue:`111`)
- Skipping cash validation where there are open orders (:issue:`144`)

Version 0.4.3
^^^^^^^^^^^^^
**Release Date**: 2018-01-05

Bug Fixes
~~~~~~~~~
- Fixed CLI issue (:issue:`137`)
- Upgraded CCXT

Version 0.4.2
^^^^^^^^^^^^^
**Release Date**: 2018-01-03

Bug Fixes
~~~~~~~~~
- Fixed cash synchronization issue (:issue:`133`)
- Fixed positions synchronization issue (:issue:`132`)
- Patched empyrical to resolve a np.log1p issue (:issue:`126`)
- Fixed a paper trading issue (:issue:`124`)
- Fixed a commission issue (:issue:`104`)
- Fixed a poloniex specific issue in live trading (:issue:`103`)

Build
~~~~~
- Caching CCXT market info to limit round-trips (:issue:`99`)
- Tentative support for Pipeline (:issue:`96`)

Version 0.4.0
^^^^^^^^^^^^^
**Release Date**: 2017-12-12

Bug Fixes
~~~~~~~~~

- Changed Poloniex interface (should solve :issue:`95` and :issue:`94`)
- Solved issue with overriding commission and slippage (:issue:`87`)
- Fixed inefficiency with Bittrex current prices (:issue:`76`)

Build
~~~~~
- Integrated with CCXT
- Added paper trading capability (`simulate_orders=True` param in live mode)
- More granular commissions (:issue:`82`)
- Added market orders in live mode (:issue:`81`)

Version 0.3.10
~~~~~~~~~~~~~~
**Release Date**: 2017-11-28

Bug Fixes
~~~~~~~~~

- Fixed issue with fetching assets with daily frequency

Version 0.3.9
^^^^^^^^^^^^^
**Release Date**: 2017-11-28

Bug Fixes
~~~~~~~~~

- Fixed sortino warning issues (:issue:`77`)
- Adjusted computation of last candle of data.history (:issue:`71`)

Build
~~~~~
- Added capital_base parameter to live mode to limit cash (:issue:`79`)
- Added support for csv ingestion (:issue:`65`)
- Improved cash display in running stats (:issue:`80`)


Version 0.3.8
^^^^^^^^^^^^^
**Release Date**: 2017-11-14

Bug Fixes
~~~~~~~~~

- Fixed a warning filter issue introduced with the latest release

Version 0.3.7
^^^^^^^^^^^^^
**Release Date**: 2017-11-14

Bug Fixes
~~~~~~~~~

- Fixed an SSL cert issue (:issue:`64`)
- Fixed cumulative stats warnings (:issue:`63`)
- Disabled auto-ingestion because of unresolved caching issues (:issue:`47`)
- Standardized live-trading stats (:issue:`61`)

Build
~~~~~

- Added a mean-reversion sample algo
- Added minutely stats in the analyze() function (:issue:`62`)
- Added specificity to some error messages

Version 0.3.6
^^^^^^^^^^^^^
**Release Date**: 2017-11-4

Bug Fixes
~~~~~~~~~

- Fixed an issue with single bar data.history() (:issue:`55`)

Version 0.3.5
^^^^^^^^^^^^^
**Release Date**: 2017-11-4

Bug Fixes
~~~~~~~~~

- Added workaround for: KeyError: Timestamp error (:issue:`53`)

Version 0.3.4
^^^^^^^^^^^^^
**Release Date**: 2017-11-2

Bug Fixes
~~~~~~~~~

- Fixed issue with auto-ingestion of minute data (:issue:`47`)
- Fixed issue with sell orders in backtesting
- Fixed data frequency issues with data.history() in backtesting
- Fixed an issue with can_trade()
- Reduced the commission and slippage values to account for lower volume
  transactions

Build
~~~~~

- Added more unit tests

Documentation
~~~~~~~~~~~~~

- Improved installation notes for Windows C++ compiler and Conda
- Addition of
  `Jupyter Notebook guide <https://enigmampc.github.io/catalyst/jupyter.html>`_
- Addition of
  `Live Trading page <https://enigmampc.github.io/catalyst/live-trading.html>`_
- Addition of
  `Videos page <https://enigmampc.github.io/catalyst/videos.html>`_
- Addition of
  `Resources page <https://enigmampc.github.io/catalyst/resources.html>`_
- Addition of `Development Guidelines
  <https://enigmampc.github.io/catalyst/development-guidelines.html>`_
- Addition of
  `Release Notes <https://enigmampc.github.io/catalyst/releases.html>`_
- Updated code docstrings


Version 0.3.3
^^^^^^^^^^^^^
**Release Date**: 2017-10-26

Bug Fixes
~~~~~~~~~

- Fix missing -x in ingest-exchange
- Fix issue with daily chunks end date (data bundles)
- Fix issue in the prepare_chunk logic (data bundles)

Build
~~~~~

- Added data validation unit tests


Version 0.3.2
^^^^^^^^^^^^^
**Release Date**: 2017-10-25

Bug Fixes
~~~~~~~~~

- Fix to work with empty data bundles
- Fix Windows path of ``$HOME/.catalyst`` folder
- Fix ``etc/python2.7-environment.yml`` for Windows Conda install
- Fix hash method to create sid numbers compatible across platforms
- Fix an issue with asset date in chunks

Build
~~~~~

- Python3 adjustments
- Added method to clean bundle folders, and remove symbols.json
- Implemented and improved unit tests


Version 0.3.1
^^^^^^^^^^^^^
**Release Date**: 2017-10-22

Bug Fixes
~~~~~~~~~

- Fixed OS-dependent path issue in data bundle
- Changed handling of empty ``auth.json``, instead of throwing an error for
  missing file
- Updated ``etc/python2.7-environment.yml`` to work with Catalyst version 0.3
- Updated ``catalyst/examples/buy_and_hodl.py``  and
  ``catalyst/examples/buy_low_sell_high.py`` to work with Catalyst version 0.3


Version 0.3
^^^^^^^^^^^
**Release Date**: 2017-10-20

- Standardized live and backtesting syntax
- Added a repository for historical data
- Added supported for multiple exchanges per algorithm
- Added a standardized dictionary of symbols for each exchange
- Added auto-ingestion of bundle data while backtesting
- Bug fixes


Version 0.2.dev5
^^^^^^^^^^^^^^^^
**Release Date**: 2017-10-03

- Fixes bug in data.history function that was formatting 'volume' data as
  integers, now they are returned as floats with up to 9 decimals of precision.
  Data bundles redone.

Version 0.2.dev4
^^^^^^^^^^^^^^^^

**Release Date**: 2017-09-20

- Fixes bug in the pricing resolution of 1-minute data, now set to 8 decimal
  places. Pricing resolution of daily data remains set to 9 decimal places.
- The current data bundle takes 340MB compressed for download, and 460MB
  uncompressed on disk for Catalyst to use.

Version 0.2.dev3
^^^^^^^^^^^^^^^^

**Release Date**: 2017-09-20

- 1-minute resolution OHLCV data bundle for backtesting from Poloniex exchange
- Implementation of trading of fractional crypto assets (i.e. 0.01 BTC)
- Minimum trade size of a coin can be configured on a per-coin basis, defaults
  to 0.00000001 in backtesting (most exchanges set the minimum trade to larger
  amounts, which will impact live trading)
- Increased pricing resolution from 3 to 9 decimal places
- The current data bundle takes 40MB compressed for download, and 99MB
  uncompressed on disk for Catalyst to use.

Version 0.2.dev2
^^^^^^^^^^^^^^^^

**Release Date**: 2017-09-07

- Fix path issue

Version 0.2.dev1
^^^^^^^^^^^^^^^^

**Release Date**: 2017-09-03

- Implementation of live trading:

  - Comprehensive trading functionality against exchanges Bitfinex and Bittrex.
  - Support for all trading pairs available on each exchange.
  - Multiple algorithms can trade simultaneously against a single exchange
    using the same account.
  - Each algorithm has a persisted state (i.e. algorithm can be stopped and
    restarted preserving the state without data loss) that tracks all open
    orders, executed transactions and portfolio positions.

- Minute by minute portfolio performance metrics.

  - Daily summary performance statistics compatible with pyfolio, a Python
    library for performance and risk analysis of financial portfolios

Version 0.1.dev9
^^^^^^^^^^^^^^^^

**Release Date**: 2017-08-28

- Retrieval of crypto benchmark from bundle, instead of hitting Poloniex
  exchange directly
- Change of bundle storage provider from Dropbox to AWS
- Fix issue with 1/1000 scaling issue of prices in bundle

Version 0.1.dev8
^^^^^^^^^^^^^^^^

**Release Date**: 2017-08-18

- Fixes issue in the creation of bundles (:issue:`27`)


Version 0.1.dev7
^^^^^^^^^^^^^^^^
- Fixes issues in empty benchmark (:issue:`16`)
- Fixes issue of normalizing timestamps before comparison (:issue:`24`)
- Generic data bundles
- CLI UI improvements

Version 0.1.dev6
^^^^^^^^^^^^^^^^

**Release Date**: 2017-07-13

- Initial public release
