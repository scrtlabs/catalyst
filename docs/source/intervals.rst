Pricing Data Intervals
----------------------

Pricing data for any asset is aggregated and stored in predetermined units of time, which are referred to as intervals or bars in a chart. Each single bar or interval captures the price movement of an asset and contains the open, high, low and closing prices for the specified period of time. For example, if a trader is working with daily data, one interval captures the price movements for one day. Analogously, if a trader is working with minute data, each interval captures the price movements for one minute.

It is important to understand the precise definition of these units of time as it affects your trading decisions. We are using the mathematical definition of `interval <https://en.wikipedia.org/wiki/Interval_(mathematics)>`_ to define a set of numbers (times) with the property that any number that lies between two numbers (start time and end time) in the set is also included in the set. The question arises in determining whether the endpoints are included in the interval or not, that is whether the intervals are open or closed.

For example, a day is defined to start at ``00:00:00`` and end at ``23:59:59``. This is a left-closed and right-opened interval, which is typically referred to as left-bound or left-closed for short (which matches `Pandas nomenclature of intervals <https://pandas.pydata.org/pandas-docs/stable/generated/pandas.Interval.html>`_). This means that midnight of a given day is only included as the endpoint of the starting day, but not the preceding day (the previous day ended right before midnight).

Stock trading
^^^^^^^^^^^^^

Counter-intuitively for novice traders, stock trading uses right-bound intervals. For example, at NYSE trading starts right after 9:30 am and ends at 4pm, and every minute is counted as follows::

	9:30:00 am < t <= 9:31:00 am First minute of a trading day
	9:31:00 am < t <= 9:32:00 am
	9:32:00 am < t <= 9:33:00 am
	...
	3:59:00 pm < t <= 4:00:00 pm Last minute of a trading day

And each interval is labeled with the ending time as follows::

	9:31 interval: 9:30:00 am < t <= 9:31:00 am and is the first minute of a trading day
	9:32 interval: 9:31:00 am < t <= 9:32:00 am
	9:33 interval: 9:32:00 am < t <= 9:33:00 am
	...
	4:00 interval: 3:59:00 pm < t <= 4:00:00 pm and is the last minute of a trading day

Essentially, the pricing data for a given minute interval is always from the previous minute. While this may seem counter-intuitive at first, it helps in preventing a `look-ahead bias <https://www.investopedia.com/terms/l/lookaheadbias.asp>`_. This means that when we trade at any given minute, we only see information that would have been available at the time of the trade (anything prior up to that point).

It is worth noting that in stock trading, day intervals are left-labeled and minute intervals are right-labeled, even though they both are defined right-bounded or right-closed. While this naming may seem inconsistent or problematic at first, it never poses a problem because stock trading is always limited to a set of hours within a day, and never involves 24/7 trading where it would cause confusion right at midnight.

The naming convention defined above is the one that `zipline <https://github.com/quantopian/zipline>`_ implements.

Crypto trading
^^^^^^^^^^^^^^

Conversely, cryptocurrency trading exchanges use left-bounded (aka left-closed and left-labeled) minute and daily intervals. For example, using the same times defined above, in crypto they would be defined as follows::

	9:31 interval: 9:31:00 am <= t < 9:32:00 am
	9:32 interval: 9:32:00 am <= t < 9:33:00 am
	9:33 interval: 9:33:00 am <= t < 9:34:00 am
	...

For reference, in zipline when the clock ticks at the beginning of every minute, it uses data from the previous minute (labeled as ending in the current minute). To meet the different nature of the crypto data definition versus the stock market data, Catalyst code had to be altered as follows: when the minute clock ticks at the beginning of every minute `data.current <appendix.html#catalyst.protocol.BarData.current>`_ returns the closing price from the previous minute and `data.history <appendix.html#catalyst.protocol.BarData.history>`_ last bar matches `data.current <appendix.html#catalyst.protocol.BarData.current>`_ providing the price up to the minute prior to the current one. 
