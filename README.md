[![Enigma | Catalyst][https://s3.amazonaws.com/enigmaco-docs/catalyst-crypto.png]][https://enigmampc.github.io/catalyst]

# Enigma | Catalyst: A Fork [![Travis CI][travis-master]][travis-url]

This is a fork of *Enigma Catalyst*, which in turn is a fork of Quantopian's Zipline algorithmic trading platform. *Catalyst* has been stale for quite some time, despite looking like a very useful platform for algorithmic trading of crypto-assets. As it stagnated Pull Requests began to build up, the Travis CI build broke, and access to historic market data ceased. This fork attempts to solve some of these issues.

## Current Progress

- **Simplified and Fixed Travis CI Build**: This may not seem like a huge deal, but it does add some safety when making other changes - courtesy of the automated testing.
- **Dependency Updates**: There were a few vulnerabilities in the existing dependencies in-use, a mixture of *Arbitrary Code Execution* and *Denial of Service* ones; these have been mitigated.
- **Fixed Installation Issues**: Installation was fundamentally broken, but there is now  Docker Image available via Docker Hub.

### Short-Term Plans

- **Merging of Existing Pull Requests**: This has began with small ones, I will slowly pull those over to this fork.
- **Merging of complete implementations from existing branches**: In a similar vein to the point above, I've created *Draft Pull Requests* for all stagnant branches which were in the base/upstream repository. I need to review them, and amend a few, but some of these appear to be quite interesting, and it would be a shame to see peoples effort go to waste.
- **Simplifying the Development Process**: At the moment this relies upon Vagrant (from what I can see), despite their being existing Docker based infrastructure. I'd like to remove all of that, including - perhaps controversially - support for Windows; there's no reason Windows support can't be provided via containerisation.

**If we make it this far, then I'll create another tag and release a proper changelog*

### Long-Term Goal

- **Real Time Trading**: Most of the crypto exchanges now support - often multiplexed - websocket connections; and with the volatility of some crypto-assets, and the subsequent market opportunities that they provide, utilising these is paramount. This does lead to a few issues - i.e `ccxt` only providing it as part of a `ccxt pro` package in the future, but it's imperative that we get a higher resolution than one candle stick per minute.
- **Dead Code Removal**: What's left from the old Quantopian days that can be removed?

> Catalyst is an algorithmic trading library for crypto-assets written in Python. It allows trading strategies to be easily expressed and backtested against historical data (with daily and minute resolution), providing analytics and insights regarding a particular strategy's performance. Catalyst also supports live-trading of crypto-assets starting with four exchanges (Binance, Bitfinex, Bittrex, and Poloniex) with more being added over time. Catalyst empowers users to share and curate data and build profitable, data-driven investment strategies. Please  visit `catalystcrypto.io <https://www.catalystcrypto.io>`_ to learn more about Catalyst.
>
> Catalyst builds on top of the well-established  `Zipline <https://github.com/quantopian/zipline>`_ project. We did our best to  minimize structural changes to the general API to maximize compatibility with existing trading algorithms, developer knowledge, and tutorials. Join us on the `Catalyst Forum <https://forum.catalystcrypto.io/>`_ for questions around Catalyst, algorithmic trading and technical support. We also have a [Discord](https://discord.gg/SJK32GY) group with the *#catalyst_dev* and *#catalyst_setup* dedicated channels.
>
> Overview
> ========
>
> -  Ease of use: Catalyst tries to get out of your way so that you can focus on algorithm development. See [examples of trading strategies](https://github.com/enigmampc/catalyst/tree/master/catalyst/examples) provided.
> -  Support for several of the top crypto-exchanges by trading volume: [Bitfinex](https://www.bitfinex.com), [Bittrex](http://www.bittrex.com), [Poloniex](https://www.poloniex.com), and [Binance](https://www.binance.com/).
> -  Secure: You and only you have access to each exchange API keys for your accounts.
> -  Input of historical pricing data of all crypto-assets by exchange, with daily and minute resolution. See  [Catalyst Market Coverage Overview](https://www.enigma.co/catalyst/status).
> -  Backtesting and live-trading functionality, with a seamless transition between the two modes.
> -  Output of performance statistics are based on Pandas DataFrames to integrate nicely into the existing PyData eco-system.
> -  Statistic and machine learning libraries like matplotlib, scipy, statsmodels, and sklearn support development, analysis, and visualization of state-of-the-art trading systems.
>-  Addition of Bitcoin price (btc_usdt) as a benchmark for comparing performance across trading algorithms.
>
> Go to our [Documentation Website](https://enigmampc.github.io/catalyst/).

[travis-master]: https://travis-ci.org/FergusInLondon/catalyst.svg?branch=master
[travis-url]: https;//travis-ci.org/FergusInLondon/catalyst
