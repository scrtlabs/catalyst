import os
import re
import sys
import warnings
from datetime import timedelta
from runpy import run_path
from time import sleep

import click
import pandas as pd

from catalyst.data.bundles import load
from catalyst.data.data_portal import DataPortal
from catalyst.exchange.bittrex.bittrex import Bittrex
from catalyst.exchange.bitfinex.bitfinex import Bitfinex
from catalyst.exchange.poloniex.poloniex import Poloniex

try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import TerminalFormatter

    PYGMENTS = True
except:
    PYGMENTS = False
from toolz import valfilter, concatv
from functools import partial

from catalyst.finance.trading import TradingEnvironment
from catalyst.utils.calendars import get_calendar
from catalyst.utils.factory import create_simulation_parameters
from catalyst.data.loader import load_crypto_market_data
import catalyst.utils.paths as pth

from catalyst.exchange.exchange_algorithm import ExchangeTradingAlgorithmLive, \
    ExchangeTradingAlgorithmBacktest
from catalyst.exchange.exchange_data_portal import DataPortalExchangeLive, \
    DataPortalExchangeBacktest
from catalyst.exchange.asset_finder_exchange import AssetFinderExchange
from catalyst.exchange.exchange_portfolio import ExchangePortfolio
from catalyst.exchange.exchange_errors import (
    ExchangeRequestError, ExchangeAuthEmpty,
    ExchangeRequestErrorTooManyAttempts,
    BaseCurrencyNotFoundError, ExchangeNotFoundError)
from catalyst.exchange.exchange_utils import get_exchange_auth, \
    get_algo_object, get_exchange_folder
from logbook import Logger

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
         base_currency,
         live_graph):
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

    mode = 'live' if live else 'backtest'
    log.info('running algo in {mode} mode'.format(mode=mode))

    exchange_name = exchange
    if exchange_name is None:
        raise ValueError('Please specify at least one exchange.')

    exchange_list = [x.strip().lower() for x in exchange.split(',')]

    exchanges = dict()
    for exchange_name in exchange_list:

        # Looking for the portfolio from the cache first
        portfolio = get_algo_object(
            algo_name=algo_namespace,
            key='portfolio_{}'.format(exchange_name),
            environ=environ
        )

        if portfolio is None:
            portfolio = ExchangePortfolio(
                start_date=pd.Timestamp.utcnow()
            )

        # This corresponds to the json file containing api token info
        exchange_auth = get_exchange_auth(exchange_name)

        if live and (exchange_auth['key'] == '' \
                             or exchange_auth['secret'] == ''):
            raise ExchangeAuthEmpty(
                exchange=exchange_name.title(),
                filename=os.path.join(
                    get_exchange_folder(exchange_name, environ), 'auth.json'))

        if exchange_name == 'bitfinex':
            exchanges[exchange_name] = Bitfinex(
                key=exchange_auth['key'],
                secret=exchange_auth['secret'],
                base_currency=base_currency,
                portfolio=portfolio
            )
        elif exchange_name == 'bittrex':
            exchanges[exchange_name] = Bittrex(
                key=exchange_auth['key'],
                secret=exchange_auth['secret'],
                base_currency=base_currency,
                portfolio=portfolio
            )
        elif exchange_name == 'poloniex':
            exchanges[exchange_name] = Poloniex(
                key=exchange_auth['key'],
                secret=exchange_auth['secret'],
                base_currency=base_currency,
                portfolio=portfolio
            )
        else:
            raise ExchangeNotFoundError(exchange_name=exchange_name)

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
    env.asset_finder = AssetFinderExchange()
    choose_loader = None  # TODO: use the DataPortal for in the algorithm class for this

    if live:
        start = pd.Timestamp.utcnow()

        # TODO: fix the end data.
        end = start + timedelta(hours=8760)

        data = DataPortalExchangeLive(
            exchanges=exchanges,
            asset_finder=env.asset_finder,
            trading_calendar=open_calendar,
            first_trading_day=pd.to_datetime('today', utc=True)
        )

        def fetch_capital_base(exchange, attempt_index=0):
            """
            Fetch the base currency amount required to bootstrap
            the algorithm against the exchange.

            The algorithm cannot continue without this value.

            :param exchange: the targeted exchange
            :param attempt_index:
            :return capital_base: the amount of base currency available for
            trading
            """
            try:
                log.debug('retrieving capital base in {} to bootstrap '
                          'exchange {}'.format(base_currency, exchange_name))
                balances = exchange.get_balances()
            except ExchangeRequestError as e:
                if attempt_index < 20:
                    log.warn(
                        'could not retrieve balances on {}: {}'.format(
                            exchange.name, e
                        )
                    )
                    sleep(5)
                    return fetch_capital_base(exchange, attempt_index + 1)

                else:
                    raise ExchangeRequestErrorTooManyAttempts(
                        attempts=attempt_index,
                        error=e
                    )

            if base_currency in balances:
                base_currency_available = balances[base_currency]
                log.info(
                    'base currency available in the account: {} {}'.format(
                        base_currency_available, base_currency
                    )
                )

                if capital_base is not None \
                        and capital_base < base_currency_available:
                    log.info(
                        'using capital base limit: {} {}'.format(
                            capital_base, base_currency
                        )
                    )
                    amount = capital_base
                else:
                    amount = base_currency_available

                return amount
            else:
                raise BaseCurrencyNotFoundError(
                    base_currency=base_currency,
                    exchange=exchange_name
                )

        combined_capital_base = 0
        for exchange_name in exchanges:
            exchange = exchanges[exchange_name]
            combined_capital_base += fetch_capital_base(exchange)

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
            live_graph=live_graph
        )
    elif exchanges:
        # Removed the existing Poloniex fork to keep things simple
        # We can add back the complexity if required.

        # I don't think that we should have arbitrary price data bundles
        # Instead, we should center this data around exchanges.
        # We still need to support bundles for other misc data, but we
        # can handle this later.

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
                  base_currency=None,
                  algo_namespace=None,
                  live_graph=False,
                  output=os.devnull):
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
    live: execute live trading
    exchange_conn: The exchange connection parameters

    Supported Exchanges
    -------------------
    bitfinex

    Returns
    -------
    perf : pd.DataFrame
        The daily performance of the algorithm.

    See Also
    --------
    catalyst.data.bundles.bundles : The available data bundles.
    """
    load_extensions(
        default_extension, extensions, strict_extensions, environ
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
        base_currency=base_currency,
        live_graph=live_graph
    )
