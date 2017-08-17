<h1>Live Trading Blueprint</h1>
The purpose of this document is to allow project contributors navigate
ongoing live trading implementation.

<h2>Components</h2>
At a high level the following components have been modified to coerce
zipline into live trading.

<h3>Exchange</h3>
Exchange is a new package which introduces the concept of cryptocurrency
exchanges to zipline. The package contains all new component
implementations adapted to charasteristics of exchanges.

```
catalyst/exchange
```

Here are some key characteristics which makes exchanges different from
equity and futures currently implemented in zipline.
* They trade around the clock.
* Currency symbols are inconsistent across exchanges.
* They trade currency pairs, i.e. the base currency is not always be USD.
This is a significant departure from the equity market. Additional
business logic will be required both to assess performance and
manage trades.
* The cryptocurrency market being relatively immature, there are still
significant price arbitrage opportunities between exchanges.
In contrast with the equity markets, trader usually trade directly
against an exchange (as oppose to using a broker). Consequently,
to extract maximum alpha, the platform should not only support
multiple exchanges, but also multiple exchanges per algorithm.
* The fee model is usually more complex than that of an equity broker.
It can vary drastically between exchanges.
* There are no splits, mergers, etc to worry about.
* Their order book is publicly available, the platform should access to
it as it can be used to drastically reduce slippage.

<h4>New Components</h4>
These components of the exchange package were added to the zipline
sources.

<h5>Exchange</h5>

```
catalyst/exchange/exchange.py
```

Abstract class which acts an interface for the implementation of
various exchanges. It also contains logic common to all exchanges.

<h5>Bitfinex</h5>

```
catalyst/exchange/bitfinex.py
```

The Bitfinex exchange implementation. It extends the Exchange class.

<h5>DataPortalExchange</h5>

```
catalyst/exchange/data_portal_exchange.py
```

Extends the zipline DataPortal to route spot data to the exchange.
This is critical because it allows the algoritm to request data in
real-time.

For example,

```python
    data.current(asset, 'price')
```

retrieves the current price of the asset, not the price at the time
of yielding the bar this is critical to minimize slippage.

<h5>ExchangeClock</h5>

```
catalyst/exchange/exchange_clock.py
```

An implementation to the zipline Clock which runs 24/7. It yeilds a
bar every minute.

<h5>AssetFinderExchange</h5>

```
catalyst/exchange/asset_finder_exchange.py
```

An alternate implementation of AssetFinder which locates each asset
against the exchanges instead of bundle databases.

For example,

```python
symbol('eth_usd')
```

retrieves an Asset object against the exchange as opposed to querying
a database of equities.

I have created a dictionary of currencies for the Bitfinex exchange.
The primary goal is to standardize the symbol notation across exchanges.
Here is a snippet of the file.
* Each key represents the exchange specific symbol.
* The symbol attribute represents the standard symbol which
should be common across exchanges for the given currency.
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

<h5>ExchangeTradingAlgorithm</h5>

```
catalyst/exchange/algorithm_exchange.py
```

Extends the TradingAlgorithm class which orchestrates the api
operations. This class brings together most of the components
described above.

<h4>Modified Components</h4>

The following components have been modified to include conditional
business logic to enable live trading.

<h5>run_algorithm</h5>

```
catalyst/utils/run_algo.py
```

The run_algorithm interface is an entry point to execute an
algorithm in zipline. This component was already modified for
the catalyst concurrency bundles. I added conditional logic to
which should not break any of the existing backtesting implementations.

At a high-level the run_algorithm method now contains two additional
parameters:
* live: If True, zipline will attempt to trade live. If False or not
specified, it will run a backtest as normal.
* exchange_conn: A dictionary containing the attributes required
to instantiate an exchange. Here is an example for Bitfinex:

```python
exchange_conn = dict(
    name='bitfinex',
    key='',
    secret=b'',
    base_currency='usd'
)
```

The following sample algorithm uses the run_algorithm interface:

```
catalyst/examples/buy_and_hold_live.py
```
