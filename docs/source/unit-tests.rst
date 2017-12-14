==========
Unit Tests
==========

Exchanges
~~~~~~~~~

Markets
-------
Sample:
    All markets in 3 random exchanges
Test:
    Fetch all TradingPair instances
Assert:
    No error

Current Ticker
------------------
Sample:
    3 random markets in each of the 3 random exchanges
Test:
    Fetch current price and volume
Assert:
    Not null and no error

Historical Price Data
---------------------
Sample:
    - 3 random markets for each of the 3 random exchanges supporting historical data
    - For each market, randomly select one supported frequency
Test:
    Fetch historical data for each market using the selected frequency
Assert:
    - No error and not blank
    - Date of each candle is consistent with the Catalyst desired pattern,
        - All candle start at fix intervals
        - Last candle partial and forward looking from the end date

Authentication and Orders
-------------------------
Sample:
    1 random market for each of 3 random authenticated exchanges
Test:
    - Create one limit order randomly buying or selling at least 10% out from the current price
    - Retrieve the open order from the exchange
    - Cancel the open order
Assert:
    No error


Bundles
~~~~~~~

Validate Bundle Data
--------------------
Sample:
    - 3 random market in bundles for exchanges supporting historical data
    - For each market, randomly selected data range available in the exchange historical data
Test:
    - Clean the target exchange bundle
    - Ingest the selected market data for the selected data range
    - Retrieve the bundle data into a dataframe
    - Retrieve the equivalent OHLCV data from the exchange into a dataframe
Assert:
    Matching data for the bundle and exchange


Algo Stats
----------
Sample:
    - 2 sample algorithms with built-in stats calculator
    - 2 KPIs both calculated by each algo and by Catalyst
Test:
    - Run each algorithm
    - Compare the results of the two methods or calculating stats
Assert:
    - Matching stats

CSV Ingestion
-------------
Sample:
    3 random CSV files containing price data
Test:
    - Ingest each CSV files
    - Validate with the exchange like in the 'Validate Bundle Data' test
Assert:
    Matching data between the bundle and the exchange

