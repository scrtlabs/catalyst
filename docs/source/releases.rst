=============
Release Notes
=============

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
- Reduced the commission and slippage values to account for lower volume transactions

Build
~~~~~

- Added more unit tests

Documentation
~~~~~~~~~~~~~

- Improved installation notes for Windows C++ compiler and Conda
- Addition of `Jupyter Notebook guide <https://enigmampc.github.io/catalyst/jupyter.html>`_
- Addition of `Live Trading page <https://enigmampc.github.io/catalyst/live-trading.html>`_
- Addition of `Videos page <https://enigmampc.github.io/catalyst/videos.html>`_
- Addition of `Resources page <https://enigmampc.github.io/catalyst/resources.html>`_
- Addition of `Development Guidelines <https://enigmampc.github.io/catalyst/development-guidelines.html>`_
- Addition of `Release Notes <https://enigmampc.github.io/catalyst/releases.html>`_
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
- Changed handling of empty ``auth.json``, instead of throwing an error for missing file
- Updated ``etc/python2.7-environment.yml`` to work with Catalyst version 0.3
- Updated ``catalyst/examples/buy_and_hodl.py``  and ``catalyst/examples/buy_low_sell_high.py`` to work with Catalyst version 0.3


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

- Fixes bug in data.history function that was formatting 'volume' data as integers, now they are returned as floats with up to 9 decimals of precision. Data bundles redone.

Version 0.2.dev4 
^^^^^^^^^^^^^^^^

**Release Date**: 2017-09-20

- Fixes bug in the pricing resolution of 1-minute data, now set to 8 decimal places. Pricing resolution of daily data remains set to 9 decimal places.
- The current data bundle takes 340MB compressed for download, and 460MB uncompressed on disk for Catalyst to use.

Version 0.2.dev3
^^^^^^^^^^^^^^^^

**Release Date**: 2017-09-20

- 1-minute resolution OHLCV data bundle for backtesting from Poloniex exchange
- Implementation of trading of fractional crypto assets (i.e. 0.01 BTC)
- Minimum trade size of a coin can be configured on a per-coin basis, defaults to 0.00000001 in backtesting (most exchanges set the minimum trade to larger amounts, which will impact live trading)
- Increased pricing resolution from 3 to 9 decimal places
- The current data bundle takes 40MB compressed for download, and 99MB uncompressed on disk for Catalyst to use.

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
  - Multiple algorithms can trade simultaneously against a single exchange using the same account.
  - Each algorithm has a persisted state (i.e. algorithm can be stopped and restarted preserving the state without data loss) that tracks all open orders, executed transactions and portfolio positions.

- Minute by minute portfolio performance metrics.

  - Daily summary performance statistics compatible with pyfolio, a Python library for performance and risk analysis of financial portfolios

Version 0.1.dev9
^^^^^^^^^^^^^^^^

**Release Date**: 2017-08-28

- Retrieval of crypto benchmark from bundle, instead of hitting Poloniex exchange directly
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

