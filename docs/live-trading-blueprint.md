<h1>Live Trading Blueprint</h1>
The purpose of this document is to allow project contributors navigate
through the ongoing live trading implementation.

<h2>Components</h2>
At a high level, the following components have been implemented to coerce
zipline into live trading.

<h3>Exchange</h3>

*catalyst/exchange*

Exchange is a new package introducing cryptocurrency
exchanges to zipline. The package contains mostly new implementations
of existing components, adapted to characteristics of exchanges.

Here are some key characteristics which make cryptocurrency exchanges
exchanges different compared to equity brokers.
* They trade around the clock.
* Currency symbols are inconsistent across exchanges.
* They trade currency pairs (i.e. the quote currency is not always be USD).
This is a paradigm shift in context of zipline. Additional
business logic will be required to manage the portfolio data and orders.
* The price of a single asset might vary across exchanges. This means
arbitrage opportunities. Consequently, to extract maximum alpha, the
platform should not only support multiple exchanges, but also multiple
exchanges per algorithm.
* The fee model is usually more complex than that of an equity broker.
It can vary drastically between exchanges.
* There are no splits, mergers, etc. to worry about.
* A complete order book is usually available, the platform should
offer access to it order to help traders reduce slippage.

<h3>New Components</h3>
These components of the exchange package were added to the zipline
sources.

<h4>Exchange</h4>

*catalyst/exchange/exchange.py*

Abstract class which acts as an interface for the implementation of
various exchanges. It also contains logic common to all exchanges.

<h4>Bitfinex</h4>

*catalyst/exchange/bitfinex.py*

The Bitfinex exchange implementation. It extends the Exchange class.

<h4>DataPortalExchange</h4>

*catalyst/exchange/data_portal_exchange.py*

Extends the zipline DataPortal to route spot data to the exchange.
This is critical because it allows the algoritm to request data in
real-time.

For example, `data.current(asset, 'price')` retrieves the current price
of the asset, not the price at the time of yielding the bar this
is critical to minimize slippage.

At the time of writing, it only supports spot data but I believe that
it should be extended to historical data as well. Some exchanges
have better historical data APIs than others. This will need to
be considered during each individual implementation.

<h4>ExchangeClock</h4>

*catalyst/exchange/exchange_clock.py*

An implementation to the zipline Clock which runs 24/7. It yields a
bar every minute.

<h4>AssetFinderExchange</h4>

*catalyst/exchange/asset_finder_exchange.py*

An alternate implementation of AssetFinder which locates each asset
against the exchanges instead of bundle databases.

For example, `symbol('eth_usd')` should return an Ethereum/USD asset
regardless of currency notation of the target exchange.

To acheive this, I have created a dictionary of currencies for the
Bitfinex exchange. Here is what it looks like.
* Each key represents the exchange specific symbol.
* The symbol attribute represents the abstract symbol common across
all exchanges for the given currency.
* The start_date attribute should correspond to its first trading day
on the exchange.

```json
{
  "btcusd": {
    "symbol": "btc_usd",
    "start_date": "2010-01-01"
  },
  "ltcusd": {
    "symbol": "ltc_usd",
    "start_date": "2010-01-01"
  },
  "ltcbtc": {
    "symbol": "ltc_btc",
    "start_date": "2010-01-01"
  },
  "ethusd": {
    "symbol": "eth_usd",
    "start_date": "2010-01-01"
  },
  "ethbtc": {
    "symbol": "eth_btc",
    "start_date": "2010-01-01"
  }
}
```

<h4>ExchangeTradingAlgorithm</h4>

*catalyst/exchange/algorithm_exchange.py*

Extends the TradingAlgorithm class which orchestrates the api
operations. This class brings together most of the components
described above.

<h3>Modified Components</h3>

The following components have been modified to include conditional
business logic to enable live trading.

<h4>run_algorithm</h4>

*catalyst/utils/run_algo.py*

The run_algorithm interface is an entry point to execute an
algorithm in zipline. This component was already modified for
the catalyst concurrency bundles. I added conditional logic
which should not interfere with backtesting.

In a nutshell, the run_algorithm method now contains three additional
parameters:
* live: If True, zipline will attempt to trade live. If False or not
specified, it will run a backtest as normal.
* algo_namespace: An arbitrary namespace for the current algorithm.
It will be used to persist data between runs.
* exchange_conn: A dictionary containing the attributes required
to instantiate an exchange. Here is an example for Bitfinex:

```python
exchange_conn = dict(
    name='bitfinex',
    key='',
    secret=b'',
    quote_currency='usd'
)
```

The following sample algorithm uses the run_algorithm interface:

*catalyst/examples/buy_and_hold_live.py*

<h2>Portfolio Management</h2>

Zipline has a Portfolio class containing key metrics used by zipline
for, but not only, these reasons:

* Placing orders: When placing orders (e.g. order_target_percent),
zipline queries the portfolio to assess the size of current positions,
cash available, etc.
* Measuring performance: The portfolio contains attributes like
cost basis of each asset, p&l, etc. which zipline uses to compute all
of its performance criteria.

When backtesting, zipline automatically updates the Portfolio object
of its corresponding algorithm. When live trading, these updates should
be the responsibility of the exchange as it holds the truth for:

* Executed price of each order (including fees and slippage)
* Partial / failed orders
* Cash (i.e. quote currency) available
* Cost basis of each position

If each exchange account had a one-to-one relationship with an
algorithm, portfolio metrics could be retrieved directly from the
exchange without persisting any data to the algorithm. However,
doing this would have at least the following drawbacks:

* It may not be reasonable to ask users to dedicate an
exchange account to a single algorithm. Exchanges are not easy
to partition.
* If an exchange account contains existing positions, the calculated
cost basis would correspond to all positions, not just those
initiated by the algorithm.
* It would not be possible impose trading limits on algorithms.

It follows that Portfolio metrics should be calculated using a strategic
combination of the exchange data and algorithm activity. While tracking
the activity of an algorithm works well in backtesting, it is more
challenging during live trading. A live algorithm might run over
several months. It might have to stop and start for many reasons.
This means that the platform should have the ability to persist
algorithm activity in order to be reliable.

In the interest of time, I will start by persisting algorithm
activity in memory. Data will be lost when the algorithm execution stops.
The intent it to offer a simple basis from which to implement data
persistence strategies in the future.