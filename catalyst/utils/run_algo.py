import os
import re
from runpy import run_path
import sys
import warnings

import click
try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import TerminalFormatter
    PYGMENTS = True
except:
    PYGMENTS = False
from toolz import valfilter, concatv
from functools import partial

from catalyst.algorithm import TradingAlgorithm
from catalyst.data.bundles.core import load
from catalyst.data.data_portal import DataPortal
from catalyst.data.loader import load_crypto_market_data
from catalyst.finance.trading import TradingEnvironment
from catalyst.pipeline.data import USEquityPricing, CryptoPricing
from catalyst.pipeline.loaders import (
    USEquityPricingLoader,
    CryptoPricingLoader,
)
from catalyst.utils.calendars import get_calendar
from catalyst.utils.factory import create_simulation_parameters
import catalyst.utils.paths as pth


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
         environ):
    """Run a backtest for the given algorithm.

    This is shared between the cli and :func:`catalyst.run_algo`.
    """
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

    if bundle is not None:
        bundles = bundle.split(',')

        def get_trading_env_and_data(bundles):
            env = data = None

            b = 'poloniex'
            if len(bundles) == 0:
                return env, data
            elif len(bundles) == 1:
                b = bundles[0]

            bundle_data = load(
                b,
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

            open_calendar = get_calendar('OPEN')

            env = TradingEnvironment(
                load=partial(load_crypto_market_data, environ=environ),
                bm_symbol='USDT_BTC',
                trading_calendar=open_calendar,
                asset_db_path=connstr,
                environ=environ,
            )

            first_trading_day = bundle_data.minute_bar_reader.first_trading_day

            data = DataPortal(
                env.asset_finder,
                open_calendar,
                first_trading_day=first_trading_day,
                minute_reader=bundle_data.minute_bar_reader,
                five_minute_reader=bundle_data.five_minute_bar_reader,
                daily_reader=bundle_data.daily_bar_reader,
                adjustment_reader=bundle_data.adjustment_reader,
            )

            return env, data

        def get_loader_for_bundle(b):
            bundle_data = load(
                b,
                environ,
                bundle_timestamp,
            )

            if b == 'poloniex':
                return CryptoPricingLoader(
                           bundle_data,
                           data_frequency,
                           CryptoPricing,
                       )
            elif b == 'quandl':
                return USEquityPricingLoader(
                           bundle_data,
                           data_frequency,
                           USEquityPricing,
                       )
            raise ValueError(
                "No PipelineLoader registered for bundle %s." % b
            )

        loaders = [get_loader_for_bundle(b) for b in bundles]
        env, data = get_trading_env_and_data(bundles)

        def choose_loader(column):
            for loader in loaders:
                if column in loader.columns:
                    return loader
            raise ValueError(
                "No PipelineLoader registered for column %s." % column
            )

    else:
        env = TradingEnvironment(environ=environ)
        choose_loader = None

    perf = TradingAlgorithm(
        namespace=namespace,
        env=env,
        get_pipeline_loader=choose_loader,
        sim_params=create_simulation_parameters(
            start=start,
            end=end,
            capital_base=capital_base,
            data_frequency=data_frequency,
            emission_rate=data_frequency,
        ),
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


def run_algorithm(start,
                  end,
                  initialize,
                  capital_base,
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
                  environ=os.environ):
    """Run a trading algorithm.

    Parameters
    ----------
    start : datetime
        The start date of the backtest.
    end : datetime
        The end date of the backtest..
    initialize : callable[context -> None]
        The initialize function to use for the algorithm. This is called once
        at the very begining of the backtest and should be used to set up
        any state needed by the algorithm.
    capital_base : float
        The starting capital for the backtest.
    handle_data : callable[(context, BarData) -> None], optional
        The handle_data function to use for the algorithm. This is called
        every minute when ``data_frequency == 'minute'`` or every day
        when ``data_frequency == 'daily'``.
    before_trading_start : callable[(context, BarData) -> None], optional
        The before_trading_start function for the algorithm. This is called
        once before each trading day (after initialize on the first day).
    analyze : callable[(context, pd.DataFrame) -> None], optional
        The analyze function to use for the algorithm. This function is called
        once at the end of the backtest and is passed the context and the
        performance data.
    data_frequency : {'daily', 'minute'}, optional
        The data frequency to run the algorithm at.
    data : pd.DataFrame, pd.Panel, or DataPortal, optional
        The ohlcv data to run the backtest with.
        This argument is mutually exclusive with:
        ``bundle``
        ``bundle_timestamp``
    bundle : str, optional
        The name of the data bundle to use to load the data to run the backtest
        with. This defaults to 'quantopian-quandl'.
        This argument is mutually exclusive with ``data``.
    bundle_timestamp : datetime, optional
        The datetime to lookup the bundle data for. This defaults to the
        current time.
        This argument is mutually exclusive with ``data``.
    default_extension : bool, optional
        Should the default catalyst extension be loaded. This is found at
        ``$ZIPLINE_ROOT/extension.py``
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

    Returns
    -------
    perf : pd.DataFrame
        The daily performance of the algorithm.

    See Also
    --------
    catalyst.data.bundles.bundles : The available data bundles.
    """
    load_extensions(default_extension, extensions, strict_extensions, environ)

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
        output=os.devnull,
        print_algo=False,
        local_namespace=False,
        environ=environ,
    )
