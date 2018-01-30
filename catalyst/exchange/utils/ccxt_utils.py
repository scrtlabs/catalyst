import json
import os
import pandas as pd
from six.moves.urllib import request

from catalyst.assets._assets import TradingPair
from ccxt import NetworkError
from catalyst.constants import LOG_LEVEL, EXCHANGE_CONFIG_URL
from catalyst.exchange.exchange_errors import MarketsNotFoundError, \
    InvalidMarketError
from catalyst.exchange.utils.exchange_utils import get_catalyst_symbol, \
    get_exchange_folder, get_exchange_auth
from catalyst.exchange.utils.serialization_utils import ExchangeJSONDecoder, \
    ExchangeJSONEncoder
from logbook import Logger
from redo import retry
from ccxt.base.exchange import Exchange
from catalyst.utils.paths import last_modified_time, data_root, \
    ensure_directory
import ccxt

log = Logger('ccxt_utils', level=LOG_LEVEL)


def scan_exchange_configs(features=None, history=None, is_authenticated=False,
                          path=None):
    """
    Finding exchanges from their config files

    Parameters
    ----------
    features
    is_authenticated

    Returns
    -------

    """
    for exchange_name in ccxt.exchanges:
        config = get_exchange_config(exchange_name, path)
        if not config or 'error' in config:
            log.info(
                'skipping invalid exchange {}'.format(exchange_name)
            )

        # Check if the exchange has an auth.json file
        if is_authenticated:
            exchange_auth = get_exchange_auth(exchange_name)
            has_auth = (exchange_auth['key'] != ''
                        and exchange_auth['secret'] != '')

            if not has_auth:
                continue

        if features is None:
            has_features = True

        else:
            try:
                supported_features = [
                    feature for feature in features if
                    feature in config['features']
                ]
                has_features = len(supported_features) > 0
            except Exception:
                has_features = False

        # TODO: filter by history
        if has_features:
            yield config


def get_exchange_config(exchange_name, path=None, environ=None,
                        expiry='2H'):
    """
    The de-serialized content of the exchange's config.json.
    Parameters
    ----------
    exchange_name: str
        The exchange name
    filename: str
        The target file
    environ:

    Returns
    -------
    config: dict[srt, Object]
        The config dictionary.

    """
    try:
        if path is None:
            root = data_root(environ)
            path = os.path.join(root, 'exchanges')

        folder = os.path.join(path, exchange_name)
        ensure_directory(folder)

        filename = os.path.join(folder, 'config.json')
        url = EXCHANGE_CONFIG_URL.format(exchange=exchange_name)
        if os.path.isfile(filename):
            # If the file exists, only update periodically to avoid
            # unnecessary calls
            now = pd.Timestamp.utcnow()
            limit = pd.Timedelta(expiry)
            if pd.Timedelta(now - last_modified_time(filename)) > limit:
                try:
                    request.urlretrieve(url=url, filename=filename)
                except Exception as e:
                    log.warn(
                        'unable to update config {} => {}: {}'.format(
                            url, filename, e
                        )
                    )

        else:
            request.urlretrieve(url=url, filename=filename)

        with open(filename) as data_file:
            data = json.load(data_file, cls=ExchangeJSONDecoder)
            return data

    except Exception as e:
        log.warn(
            'unable to download {} config: {}'.format(
                exchange_name, e
            )
        )
        return dict(error=e)


def save_exchange_config(config, filename=None, environ=None):
    """
    Save assets into an exchange_config file.
    Parameters
    ----------
    exchange_name: str
    config
    environ
    Returns
    -------
    """
    if filename is None:
        name = 'config.json'
        exchange_folder = get_exchange_folder(config['id'], environ)
        filename = os.path.join(exchange_folder, name)

    with open(filename, 'w+') as handle:
        json.dump(config, handle, indent=4, cls=ExchangeJSONEncoder)


def fetch_markets(ccxt_exchange):
    """
    Fetches CCXT market objects.
    
    Parameters
    ----------
    ccxt_exchange: Exchange

    Returns
    -------

    """
    markets_symbols = ccxt_exchange.load_markets()
    log.debug(
        'fetching {} markets:\n{}'.format(
            ccxt_exchange.name, markets_symbols
        )
    )
    markets = ccxt_exchange.fetch_markets()

    if not markets:
        raise MarketsNotFoundError(
            exchange=ccxt_exchange.name,
        )

    for market in markets:
        if 'id' not in market:
            raise InvalidMarketError(
                exchange=ccxt_exchange.name,
                market=market,
            )
    return markets


def create_exchange_config(ccxt_exchange):
    """
    Creates an exchange config structure. 
    
    Parameters
    ----------
    ccxt_exchange: Exchange

    Returns
    -------

    """
    exchange_name = ccxt_exchange.__class__.__name__
    config = dict(
        id=exchange_name,
        name=ccxt_exchange.name,
        features=[
            feature for feature in ccxt_exchange.has if
            ccxt_exchange.has[feature]
        ]
    )
    markets = retry(
        action=fetch_markets,
        attempts=5,
        sleeptime=5,
        retry_exceptions=(NetworkError,),
        cleanup=lambda: log.warn(
            'fetching markets again for {}'.format(exchange_name)
        ),
        args=(ccxt_exchange,)
    )

    config['assets'] = []
    for market in markets:
        asset = create_trading_pair(exchange_name, market)
        config['assets'].append(asset)

    return config


def create_trading_pair(exchange_name, market, start_dt=None, end_dt=None,
                        leverage=1, end_daily=None, end_minute=None):
    """
    Creating a TradingPair from market and asset data.

    Parameters
    ----------
    market: dict[str, Object]
    start_dt
    end_dt
    leverage
    end_daily
    end_minute

    Returns
    -------

    """
    params = dict(
        exchange=exchange_name,
        data_source='catalyst',
        exchange_symbol=market['id'],
        symbol=get_catalyst_symbol(market),
        start_date=start_dt,
        end_date=end_dt,
        leverage=leverage,
        asset_name=market['symbol'],
        end_daily=end_daily,
        end_minute=end_minute,
    )
    apply_conditional_market_params(exchange_name, params, market)

    return TradingPair(**params)


def apply_conditional_market_params(exchange_name, params, market):
    """
    Applies a CCXT market dict to parameters of TradingPair init.

    Parameters
    ----------
    params: dict[Object]
    market: dict[Object]

    Returns
    -------

    """
    # TODO: make this more externalized / configurable
    # Consider representing in some type of JSON structure
    if 'active' in market:
        params['trading_state'] = 1 if market['active'] else 0

    else:
        params['trading_state'] = 1

    if 'lot' in market:
        params['min_trade_size'] = market['lot']
        params['lot'] = market['lot']

    if exchange_name == 'bitfinex':
        params['maker'] = 0.001
        params['taker'] = 0.002

    elif 'maker' in market and 'taker' in market \
        and market['maker'] is not None \
        and market['taker'] is not None:
        params['maker'] = market['maker']
        params['taker'] = market['taker']

    else:
        # TODO: default commission, make configurable
        params['maker'] = 0.0015
        params['taker'] = 0.0025

    info = market['info'] if 'info' in market else None
    if info:
        if 'minimum_order_size' in info:
            params['min_trade_size'] = float(info['minimum_order_size'])

            if 'lot' not in params:
                params['lot'] = params['min_trade_size']
