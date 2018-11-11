API Reference
-------------

Running a Strategy
~~~~~~~~~~~~~~~~~~

.. autofunction:: catalyst.run_algorithm(...)

Algorithm API
~~~~~~~~~~~~~

The following methods are available for use in the ``initialize``,
``handle_data``, and ``before_trading_start`` API functions.

In all listed functions, the ``self`` argument is implicitly the
currently-executing :class:`~catalyst.algorithm.TradingAlgorithm` instance.

Data Object
```````````

.. autoclass:: catalyst.protocol.BarData
   :members:



Scheduling Functions
````````````````````

.. autofunction:: catalyst.api.schedule_function

.. autoclass:: catalyst.api.date_rules
   :members:
   :undoc-members:

.. autoclass:: catalyst.api.time_rules
   :members:

Orders
``````

.. autofunction:: catalyst.api.order

.. autofunction:: catalyst.api.order_value

.. autofunction:: catalyst.api.order_percent

.. autofunction:: catalyst.api.order_target

.. autofunction:: catalyst.api.order_target_value

.. autofunction:: catalyst.api.order_target_percent

.. autoclass:: catalyst.finance.execution.ExecutionStyle
..   :members:

.. autoclass:: catalyst.finance.execution.MarketOrder

.. autoclass:: catalyst.finance.execution.LimitOrder

.. .. autoclass:: catalyst.finance.execution.StopOrder

.. .. autoclass:: catalyst.finance.execution.StopLimitOrder

.. autofunction:: catalyst.api.get_order

.. autofunction:: catalyst.api.get_open_orders

.. autofunction:: catalyst.api.cancel_order

.. autofunction:: catalyst.api.get_orderbook


Order Cancellation Policies
'''''''''''''''''''''''''''

.. autofunction:: catalyst.api.set_cancel_policy

.. autoclass:: catalyst.finance.cancel_policy.CancelPolicy
   :members:

.. autofunction:: catalyst.api.EODCancel

.. autofunction:: catalyst.api.NeverCancel


Assets
``````

.. autofunction:: catalyst.api.symbol

.. autofunction:: catalyst.api.symbols

.. .. autofunction:: catalyst.api.set_symbol_lookup_date

.. autofunction:: catalyst.api.sid


.. Trading Controls
.. ````````````````

.. catalyst provides trading controls to help ensure that the algorithm is
.. performing as expected. The functions help protect the algorithm from certain
.. bugs that could cause undesirable behavior when trading with real money.

.. .. autofunction:: catalyst.api.set_do_not_order_list

.. .. autofunction:: catalyst.api.set_long_only

.. .. autofunction:: catalyst.api.set_max_leverage

.. .. autofunction:: catalyst.api.set_max_order_count

.. .. autofunction:: catalyst.api.set_max_order_size

.. .. autofunction:: catalyst.api.set_max_position_size


Simulation Parameters
`````````````````````

.. autofunction:: catalyst.api.set_benchmark

Commission Models
'''''''''''''''''

.. autofunction:: catalyst.api.set_commission

.. autoclass:: catalyst.finance.commission.CommissionModel
   :members:

.. .. autoclass:: catalyst.finance.commission.PerShare

.. .. autoclass:: catalyst.finance.commission.PerTrade

.. .. autoclass:: catalyst.finance.commission.PerDollar

Slippage Models
'''''''''''''''

.. autofunction:: catalyst.api.set_slippage

.. autoclass:: catalyst.finance.slippage.SlippageModel
   :members:

.. .. autoclass:: catalyst.finance.slippage.FixedSlippage

.. autoclass:: catalyst.exchange.exchange_blotter.TradingPairFixedSlippage

.. .. autoclass:: catalyst.finance.slippage.VolumeShareSlippage

Pipeline
````````

Not supported yet.

.. For more information, see :ref:`pipeline-api`

.. .. autofunction:: catalyst.api.attach_pipeline

.. .. autofunction:: catalyst.api.pipeline_output


Miscellaneous
`````````````

.. autofunction:: catalyst.api.record

.. autofunction:: catalyst.api.get_environment

.. .. autofunction:: catalyst.api.fetch_csv


.. _pipeline-api:

.. Pipeline API
.. ~~~~~~~~~~~~

.. .. autoclass:: zipline.pipeline.Pipeline
..    :members:
..    :member-order: groupwise

.. .. autoclass:: zipline.pipeline.CustomFactor
..    :members:
..    :member-order: groupwise

.. .. autoclass:: zipline.pipeline.filters.Filter
..    :members: __and__, __or__
..    :exclude-members: dtype

.. .. autoclass:: zipline.pipeline.factors.Factor
..    :members: bottom, deciles, demean, linear_regression, pearsonr,
..              percentile_between, quantiles, quartiles, quintiles, rank,
..              spearmanr, top, winsorize, zscore, isnan, notnan, isfinite, eq,
..              \__add__, \__sub__, \__mul__, \__div__, \__mod__, \__pow__, 
..              \__lt__, \__le__, \__ne__, \__ge__, \__gt__
..    :exclude-members: dtype
..    :member-order: bysource

.. .. autoclass:: zipline.pipeline.term.Term
..    :members:
..    :exclude-members: compute_extra_rows, dependencies, inputs, mask, windowed

.. .. autoclass:: zipline.pipeline.data.USEquityPricing
..    :members: open, high, low, close, volume
..    :undoc-members:

.. Built-in Factors
.. ````````````````

.. .. autoclass:: zipline.pipeline.factors.AverageDollarVolume
..    :members:

.. .. autoclass:: zipline.pipeline.factors.BollingerBands
..    :members:

.. .. autoclass:: zipline.pipeline.factors.BusinessDaysSincePreviousEvent
..    :members:

.. .. autoclass:: zipline.pipeline.factors.BusinessDaysUntilNextEvent
..    :members:

.. .. autoclass:: zipline.pipeline.factors.ExponentialWeightedMovingAverage
..    :members:

.. .. autoclass:: zipline.pipeline.factors.ExponentialWeightedMovingStdDev
..    :members:

.. .. autoclass:: zipline.pipeline.factors.Latest
..    :members:

.. .. autoclass:: zipline.pipeline.factors.MaxDrawdown
..    :members:

.. .. autoclass:: zipline.pipeline.factors.Returns
..    :members:

.. .. autoclass:: zipline.pipeline.factors.RollingLinearRegressionOfReturns
..    :members:

.. .. autoclass:: zipline.pipeline.factors.RollingPearsonOfReturns
..    :members:

.. .. autoclass:: zipline.pipeline.factors.RollingSpearmanOfReturns
..    :members:

.. .. autoclass:: zipline.pipeline.factors.RSI
..    :members:

.. .. autoclass:: zipline.pipeline.factors.SimpleMovingAverage
..    :members:

.. .. autoclass:: zipline.pipeline.factors.VWAP
..    :members:

.. .. autoclass:: zipline.pipeline.factors.WeightedAverageValue
..    :members:

.. Pipeline Engine
.. ```````````````

.. .. autoclass:: zipline.pipeline.engine.PipelineEngine
..    :members: run_pipeline, run_chunked_pipeline
..    :member-order: bysource

.. .. autoclass:: zipline.pipeline.engine.SimplePipelineEngine
..    :members: __init__, run_pipeline, run_chunked_pipeline
..    :member-order: bysource

.. .. autofunction:: zipline.pipeline.engine.default_populate_initial_workspace

.. Data Loaders
.. ````````````

.. .. autoclass:: zipline.pipeline.loaders.equity_pricing_loader.USEquityPricingLoader
..    :members: __init__, from_files, load_adjusted_array
..    :member-order: bysource

.. Asset Metadata
.. ~~~~~~~~~~~~~~

.. .. autoclass:: catalyst.assets._assets.TradingPair // TODO: add TradingPair info in a clean way
   :members:

.. .. autoclass:: catalyst.assets.AssetConvertible
..   :members:


Trading Calendar API
~~~~~~~~~~~~~~~~~~~~

.. autofunction:: catalyst.utils.calendars.get_calendar

.. autoclass:: catalyst.utils.calendars.TradingCalendar
..   :members:

.. autofunction:: catalyst.utils.calendars.register_calendar

.. autofunction:: catalyst.utils.calendars.register_calendar_type

.. autofunction:: catalyst.utils.calendars.deregister_calendar

.. autofunction:: catalyst.utils.calendars.clear_calendars


.. Data API
.. ~~~~~~~~

.. Writers
.. ```````
.. .. autoclass:: zipline.data.minute_bars.BcolzMinuteBarWriter
..    :members:

.. .. autoclass:: zipline.data.us_equity_pricing.BcolzDailyBarWriter
..    :members:

.. .. autoclass:: zipline.data.us_equity_pricing.SQLiteAdjustmentWriter
..    :members:

.. .. autoclass:: zipline.assets.AssetDBWriter
..    :members:

.. Readers
.. ```````
.. .. autoclass:: zipline.data.minute_bars.BcolzMinuteBarReader
..    :members:

.. .. autoclass:: zipline.data.us_equity_pricing.BcolzDailyBarReader
..    :members:

.. .. autoclass:: zipline.data.us_equity_pricing.SQLiteAdjustmentReader
..    :members:

.. .. autoclass:: zipline.assets.AssetFinder
..    :members:

.. .. autoclass:: zipline.data.data_portal.DataPortal
..    :members:

.. Bundles
.. ```````
.. .. autofunction:: zipline.data.bundles.register

.. .. autofunction:: zipline.data.bundles.ingest(name, environ=os.environ, date=None, show_progress=True)

.. .. autofunction:: zipline.data.bundles.load(name, environ=os.environ, date=None)

.. .. autofunction:: zipline.data.bundles.unregister

.. .. data:: zipline.data.bundles.bundles

..    The bundles that have been registered as a mapping from bundle name to bundle
..    data. This mapping is immutable and should only be updated through
..    :func:`~zipline.data.bundles.register` or
..    :func:`~zipline.data.bundles.unregister`.

.. .. autofunction:: zipline.data.bundles.yahoo_equities


.. TODO: add relevant information to this section
.. Utilities
.. ~~~~~~~~~

.. Caching
.. ```````

.. .. autoclass:: catalyst.utils.cache.CachedObject

.. .. autoclass:: catalyst.utils.cache.ExpiringCache

.. .. autoclass:: catalyst.utils.cache.dataframe_cache

.. .. autoclass:: catalyst.utils.cache.working_file

.. .. autoclass:: catalyst.utils.cache.working_dir

.. Command Line
.. ````````````
.. .. autofunction:: catalyst.utils.cli.maybe_show_progress
