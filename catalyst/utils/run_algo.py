import os
import re
import sys
import warnings
from datetime import timedelta
from runpy import run_path
from time import sleep

import click
import pandas as pd
from six import string_types

import catalyst
from catalyst.data.bundles import load
from catalyst.data.data_portal import DataPortal
from catalyst.exchange.exchange_pricing_loader import ExchangePricingLoader, \
    TradingPairPricing
from catalyst.exchange.utils.factory import get_exchange
from logbook import Logger

try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import TerminalFormatter

    PYGMENTS = True
except ImportError:
    PYGMENTS = False
from toolz import valfilter, concatv
from functools import partial

from catalyst.finance.trading import TradingEnvironment
from catalyst.utils.calendars import get_calendar
from catalyst.utils.factory import create_simulation_parameters
from catalyst.data.loader import load_crypto_market_data
import catalyst.utils.paths as pth

from catalyst.exchange.exchange_algorithm import (
    ExchangeTradingAlgorithmLive,
    ExchangeTradingAlgorithmBacktest,
)
from catalyst.exchange.exchange_data_portal import DataPortalExchangeLive, \
    DataPortalExchangeBacktest
from catalyst.exchange.exchange_asset_finder import ExchangeAssetFinder

from catalyst.constants import LOG_LEVEL

log = Logger('run_algo', level=LOG_LEVEL)


class _RunAlgoError(click.ClickException, ValueError):
    """Signal an error that should have a different message if invoked from
    the cli.

    Parameters
    ----------
    pyfunc_msg : str
        The message that will be shown when called as a python function.

    cmdline_msg : str
        The message that will be shown on the command line.
    """
    exit_code = 1

    def __init__(self, pyfunc_msg, cmdline_msg):
        super(_RunAlgoError, self).__init__(cmdline_msg)
        self.pyfunc_msg = pyfunc_msg

    def __str__(self):
        return self.pyfunc_msg


def _run(handle_data,
         initialize,
         before_trading_start,
         analyze,
         algofile,
         algotext,
         defines,
         data_frequency,
         capital_base,
         data,
         bundle,
         bundle_timestamp,
         start,
         end,
         output,
         print_algo,
         local_namespace,
         environ,
         live,
         exchange,
         algo_namespace,
         quote_currency,
         live_graph,
         analyze_live,
         simulate_orders,
         auth_aliases,
         stats_output):
    """Run a backtest for the given algorithm.

    This is shared between the cli and :func:`catalyst.run_algo`.
    """
    # TODO: refactor for more granularity
    if algotext is not None:
        if local_namespace:
            ip = get_ipython()  # noqa
            namespace = ip.user_ns
        else:
            namespace = {}

        for assign in defines:
            try:
                name, value = assign.split('=', 2)
            except ValueError:
                raise ValueError(
                    'invalid define %r, should be of the form name=value' %
                    assign,
                )
            try:
                # evaluate in the same namespace so names may refer to
                # eachother
                namespace[name] = eval(value, namespace)
            except Exception as e:
                raise ValueError(
                    'failed to execute definition for name %r: %s' % (name, e),
                )
    elif defines:
        raise _RunAlgoError(
            'cannot pass define without `algotext`',
            "cannot pass '-D' / '--define' without '-t' / '--algotext'",
        )
    else:
        namespace = {}
        if algofile is not None:
            algotext = algofile.read()

    if print_algo:
        if PYGMENTS:
            highlight(
                algotext,
                PythonLexer(),
                TerminalFormatter(),
                outfile=sys.stdout,
            )
        else:
            click.echo(algotext)

    log.warn(
        'Catalyst is currently in ALPHA. It is going through rapid '
        'development and it is subject to errors. Please use carefully. '
        'We encourage you to report any issue on GitHub: '
        'https://github.com/enigmampc/catalyst/issues'
    )
    log.info('Catalyst version {}'.format(catalyst.__version__))
    sleep(3)

    if live:
        if simulate_orders:
            mode = 'paper-trading'
        else:
            mode = 'live-trading'
    else:
        mode = 'backtest'

    log.info('running algo in {mode} mode'.format(mode=mode))

    exchange_name = exchange
    if exchange_name is None:
        raise ValueError('Please specify at least one exchange.')

    if isinstance(auth_aliases, string_types):
        aliases = auth_aliases.split(',')
        if len(aliases) < 2 or len(aliases) % 2 != 0:
            raise ValueError(
                'the `auth_aliases` parameter must contain an even list '
                'of comma-delimited values. For example, '
                '"binance,auth2" or "binance,auth2,bittrex,auth2".'
            )

        auth_aliases = dict(zip(aliases[::2], aliases[1::2]))

    exchange_list = [x.strip().lower() for x in exchange.split(',')]
    exchanges = dict()
    for name in exchange_list:
        if auth_aliases is not None and name in auth_aliases:
            auth_alias = auth_aliases[name]
        else:
            auth_alias = None

        exchanges[name] = get_exchange(
            exchange_name=name,
            quote_currency=quote_currency,
            must_authenticate=(live and not simulate_orders),
            skip_init=True,
            auth_alias=auth_alias,
        )

    open_calendar = get_calendar('OPEN')

    env = TradingEnvironment(
        load=partial(
            load_crypto_market_data,
            environ=environ,
            start_dt=start,
            end_dt=end
        ),
        environ=environ,
        exchange_tz='UTC',
        asset_db_path=None  # We don't need an asset db, we have exchanges
    )
    env.asset_finder = ExchangeAssetFinder(exchanges=exchanges)

    def choose_loader(column):
        bound_cols = TradingPairPricing.columns
        if column in bound_cols:
            return ExchangePricingLoader(data_frequency)
        raise ValueError(
            "No PipelineLoader registered for column %s." % column
        )

    if live:
        # TODO: fix the start data.
        # is_start checks if a start date was specified by user
        # needed for live clock
        is_start = True

        if start is None:
            start = pd.Timestamp.utcnow()
            is_start = False
        elif start:
            assert pd.Timestamp.utcnow() <= start, \
                "specified start date is in the past."
        elif start and end:
            assert start < end, "start date is later than end date."

        # TODO: fix the end data.
        # is_end checks if an end date was specified by user
        # needed for live clock
        is_end = True

        if end is None:
            end = start + timedelta(hours=8760)
            is_end = False

        data = DataPortalExchangeLive(
            exchanges=exchanges,
            asset_finder=env.asset_finder,
            trading_calendar=open_calendar,
            first_trading_day=pd.to_datetime('today', utc=True)
        )

        sim_params = create_simulation_parameters(
            start=start,
            end=end,
            capital_base=capital_base,
            emission_rate='minute',
            data_frequency='minute'
        )

        # TODO: use the constructor instead
        sim_params._arena = 'live'

        algorithm_class = partial(
            ExchangeTradingAlgorithmLive,
            exchanges=exchanges,
            algo_namespace=algo_namespace,
            live_graph=live_graph,
            simulate_orders=simulate_orders,
            stats_output=stats_output,
            analyze_live=analyze_live,
            start=start,
            is_start=is_start,
            end=end,
            is_end=is_end,
        )
    elif exchanges:
        # Removed the existing Poloniex fork to keep things simple
        # We can add back the complexity if required.

        # I don't think that we should have arbitrary price data bundles
        # Instead, we should center this data around exchanges.
        # We still need to support bundles for other misc data, but we
        # can handle this later.

        if (start and start != pd.tslib.normalize_date(start)) or \
                (end and end != pd.tslib.normalize_date(end)):
            # todo: add to Sim_Params the option to
            # start & end at specific times
            log.warn(
                "Catalyst currently starts and ends on the start and "
                "end of the dates specified, respectively. We hope to "
                "Modify this and support specific times in a future release."
            )

        data = DataPortalExchangeBacktest(
            exchange_names=[exchange_name for exchange_name in exchanges],
            asset_finder=None,
            trading_calendar=open_calendar,
            first_trading_day=start,
            last_available_session=end
        )

        sim_params = create_simulation_parameters(
            start=start,
            end=end,
            capital_base=capital_base,
            data_frequency=data_frequency,
            emission_rate=data_frequency,
        )

        algorithm_class = partial(
            ExchangeTradingAlgorithmBacktest,
            exchanges=exchanges
        )

    elif bundle is not None:
        bundle_data = load(
            bundle,
            environ,
            bundle_timestamp,
        )

        prefix, connstr = re.split(
            r'sqlite:///',
            str(bundle_data.asset_finder.engine.url),
            maxsplit=1,
        )
        if prefix:
            raise ValueError(
                "invalid url %r, must begin with 'sqlite:///'" %
                str(bundle_data.asset_finder.engine.url),
            )

        env = TradingEnvironment(asset_db_path=connstr, environ=environ)
        first_trading_day = \
            bundle_data.equity_minute_bar_reader.first_trading_day

        data = DataPortal(
            env.asset_finder, open_calendar,
            first_trading_day=first_trading_day,
            equity_minute_reader=bundle_data.equity_minute_bar_reader,
            equity_daily_reader=bundle_data.equity_daily_bar_reader,
            adjustment_reader=bundle_data.adjustment_reader,
        )

    perf = algorithm_class(
        namespace=namespace,
        env=env,
        get_pipeline_loader=choose_loader,
        sim_params=sim_params,
        **{
            'initialize': initialize,
            'handle_data': handle_data,
            'before_trading_start': before_trading_start,
            'analyze': analyze,
        } if algotext is None else {
            'algo_filename': getattr(algofile, 'name', '<algorithm>'),
            'script': algotext,
        }
    ).run(
        data,
        overwrite_sim_params=False,
    )

    if output == '-':
        click.echo(str(perf))
    elif output != os.devnull:  # make the catalyst magic not write any data
        perf.to_pickle(output)

    return perf


# All of the loaded extensions. We don't want to load an extension twice.
_loaded_extensions = set()


def load_extensions(default, extensions, strict, environ, reload=False):
    """Load all of the given extensions. This should be called by run_algo
    or the cli.

    Parameters
    ----------
    default : bool
        Load the default exension (~/.catalyst/extension.py)?
    extension : iterable[str]
        The paths to the extensions to load. If the path ends in ``.py`` it is
        treated as a script and executed. If it does not end in ``.py`` it is
        treated as a module to be imported.
    strict : bool
        Should failure to load an extension raise. If this is false it will
        still warn.
    environ : mapping
        The environment to use to find the default extension path.
    reload : bool, optional
        Reload any extensions that have already been loaded.
    """
    if default:
        default_extension_path = pth.default_extension(environ=environ)
        pth.ensure_file(default_extension_path)
        # put the default extension first so other extensions can depend on
        # the order they are loaded
        extensions = concatv([default_extension_path], extensions)

    for ext in extensions:
        if ext in _loaded_extensions and not reload:
            continue
        try:
            # load all of the catalyst extensionss
            if ext.endswith('.py'):
                run_path(ext, run_name='<extension>')
            else:
                __import__(ext)
        except Exception as e:
            if strict:
                # if `strict` we should raise the actual exception and fail
                raise
            # without `strict` we should just log the failure
            warnings.warn(
                'Failed to load extension: %r\n%s' % (ext, e),
                stacklevel=2
            )
        else:
            _loaded_extensions.add(ext)


def run_algorithm(initialize,
                  capital_base=None,
                  start=None,
                  end=None,
                  handle_data=None,
                  before_trading_start=None,
                  analyze=None,
                  data_frequency='daily',
                  data=None,
                  bundle=None,
                  bundle_timestamp=None,
                  default_extension=True,
                  extensions=(),
                  strict_extensions=True,
                  environ=os.environ,
                  live=False,
                  exchange_name=None,
                  quote_currency=None,
                  algo_namespace=None,
                  live_graph=False,
                  analyze_live=None,
                  simulate_orders=True,
                  auth_aliases=None,
                  stats_output=None,
                  output=os.devnull):
    """
    Run a trading algorithm.

    Parameters
    ----------
    capital_base : float
        The starting capital for the backtest.
    start : datetime
        The start date of the backtest.
    end : datetime
        The end date of the backtest..
    initialize : callable[context -> None]
        The initialize function to use for the algorithm. This is called once
        at the very beginning of the run and should be used to set up
        any state needed by the algorithm.
    handle_data : callable[(context, BarData) -> None], optional
        The handle_data function to use for the algorithm. This is called
        every minute when ``data_frequency == 'minute'`` or every day
        when ``data_frequency == 'daily'``.
    before_trading_start : callable[(context, BarData) -> None], optional
        The before_trading_start function for the algorithm. This is called
        once before each trading day (after initialize on the first day).
    analyze : callable[(context, pd.DataFrame) -> None], optional
        The analyze function to use for the algorithm. This function is called
        once at the end of the backtest/live run and is passed the
        context and the performance data.
    data_frequency : {'daily', 'minute'}, optional
        The data frequency to run the algorithm at.
        At backtest both modes are supported, at live mode only
        the minute mode is supported.
    data : pd.DataFrame, pd.Panel, or DataPortal, optional
        The ohlcv data to run the backtest with.
        This argument is mutually exclusive with:
        ``bundle``
        ``bundle_timestamp``
    bundle : str, optional
        The name of the data bundle to use to load the data to run the backtest
        with.
        This argument is mutually exclusive with ``data``.
    bundle_timestamp : datetime, optional
        The datetime to lookup the bundle data for. This defaults to the
        current time.
        This argument is mutually exclusive with ``data``.
    default_extension : bool, optional
        Should the default catalyst extension be loaded. This is found at
        ``$CATALYST_ROOT/extension.py``
    extensions : iterable[str], optional
        The names of any other extensions to load. Each element may either be
        a dotted module path like ``a.b.c`` or a path to a python file ending
        in ``.py`` like ``a/b/c.py``.
    strict_extensions : bool, optional
        Should the run fail if any extensions fail to load. If this is false,
        a warning will be raised instead.
    environ : mapping[str -> str], optional
        The os environment to use. Many extensions use this to get parameters.
        This defaults to ``os.environ``.
    live : bool, optional
        Should the algorithm be executed in live trading mode.
    exchange_name: str
        The name of the exchange to be used in the backtest/live run.
    quote_currency: str
        The base currency to be used in the backtest/live run.
    algo_namespace: str
        The namespace of the algorithm.
    live_graph: bool, optional
        Should the live graph clock be used instead of the regular clock.
    analyze_live: callable[(context, pd.DataFrame) -> None], optional
        The interactive analyze function to be used with
        the live graph clock in every tick.
    simulate_orders: bool, optional
        Should paper trading mode be applied.
    auth_aliases: str, optional
        Rewrite the auth file name. It should contain an even list
        of comma-delimited values. For example: "binance,auth2,bittrex,auth2"
    stats_output: str, optional
        The URI of the S3 bucket to which to upload the performance stats.
    output: str, optional
        The output file path to which the algorithm performance
        is serialized.

    Returns
    -------
    perf : pd.DataFrame
        The daily performance of the algorithm.
    """

    load_extensions(
        default_extension, extensions, strict_extensions, environ
    )

    if capital_base is None:
        raise ValueError(
            'Please specify a `capital_base` parameter which is the maximum '
            'amount of base currency available for trading. For example, '
            'if the `capital_base` is 5ETH, the '
            '`order_target_percent(asset, 1)` command will order 5ETH worth '
            'of the specified asset.'
        )
    # I'm not sure that we need this since the modified DataPortal
    # does not require extensions to be explicitly loaded.

    # This will be useful for arbitrary non-pricing bundles but we may
    # need to modify the logic.
    if not live:
        non_none_data = valfilter(bool, {
            'data': data is not None,
            'bundle': bundle is not None,
        })
        if not non_none_data:
            # if neither data nor bundle are passed use 'quantopian-quandl'
            bundle = 'quantopian-quandl'

        elif len(non_none_data) != 1:
            raise ValueError(
                'must specify one of `data`, `data_portal`, or `bundle`,'
                ' got: %r' % non_none_data,
            )

        elif 'bundle' not in non_none_data and bundle_timestamp is not None:
            raise ValueError(
                'cannot specify `bundle_timestamp` without passing `bundle`',
            )
    return _run(
        handle_data=handle_data,
        initialize=initialize,
        before_trading_start=before_trading_start,
        analyze=analyze,
        algofile=None,
        algotext=None,
        defines=(),
        data_frequency=data_frequency,
        capital_base=capital_base,
        data=data,
        bundle=bundle,
        bundle_timestamp=bundle_timestamp,
        start=start,
        end=end,
        output=output,
        print_algo=False,
        local_namespace=False,
        environ=environ,
        live=live,
        exchange=exchange_name,
        algo_namespace=algo_namespace,
        quote_currency=quote_currency,
        live_graph=live_graph,
        analyze_live=analyze_live,
        simulate_orders=simulate_orders,
        auth_aliases=auth_aliases,
        stats_output=stats_output
    )
