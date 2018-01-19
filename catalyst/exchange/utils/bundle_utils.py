import os
import tarfile
from datetime import datetime

import numpy as np
import pandas as pd

from catalyst.data.bundles.core import download_without_progress
from catalyst.exchange.utils.exchange_utils import get_exchange_bundles_folder
import os
import tarfile
from datetime import datetime

import numpy as np
import pandas as pd

from catalyst.data.bundles.core import download_without_progress
from catalyst.exchange.utils.exchange_utils import get_exchange_bundles_folder

EXCHANGE_NAMES = ['bitfinex', 'bittrex', 'poloniex']
API_URL = 'http://data.enigma.co/api/v1'


def get_bcolz_chunk(exchange_name, symbol, data_frequency, period):
    """
    Download and extract a bcolz bundle.

    Parameters
    ----------
    exchange_name: str
    symbol: str
    data_frequency: str
    period: str

    Returns
    -------
    str
        Filename: bitfinex-daily-neo_eth-2017-10.tar.gz

    """
    root = get_exchange_bundles_folder(exchange_name)
    name = '{exchange}-{frequency}-{symbol}-{period}'.format(
        exchange=exchange_name,
        frequency=data_frequency,
        symbol=symbol,
        period=period
    )
    path = os.path.join(root, name)

    if not os.path.isdir(path):
        url = 'https://s3.amazonaws.com/enigmaco/catalyst-bundles/' \
              'exchange-{exchange}/{name}.tar.gz'.format(
            exchange=exchange_name,
            name=name)

        bytes = download_without_progress(url)
        with tarfile.open('r', fileobj=bytes) as tar:
            tar.extractall(path)

    return path


def get_df_from_arrays(arrays, periods):
    """
    A DataFrame from the specified OHCLV arrays.

    Parameters
    ----------
    arrays: Object
    periods: DateTimeIndex

    Returns
    -------
    DataFrame

    """
    ohlcv = dict()
    for index, field in enumerate(
            ['open', 'high', 'low', 'close', 'volume']):
        ohlcv[field] = arrays[index].flatten()

    df = pd.DataFrame(
        data=ohlcv,
        index=periods
    )
    return df


def range_in_bundle(asset, start_dt, end_dt, reader):
    """
    Evaluate whether price data of an asset is included has been ingested in
    the exchange bundle for the given date range.

    Parameters
    ----------
    asset: TradingPair
    start_dt: datetime
    end_dt: datetime
    reader: BcolzBarMinuteReader

    Returns
    -------
    bool

    """
    has_data = True
    dates = [start_dt, end_dt]

    while dates and has_data:
        try:
            dt = dates.pop(0)
            close = reader.get_value(asset.sid, dt, 'close')

            if np.isnan(close):
                has_data = False

        except Exception:
            has_data = False

    return has_data


def get_assets(exchange, include_symbols, exclude_symbols):
    """
    Get assets from an exchange, including or excluding the specified
    symbols.

    Parameters
    ----------
    exchange: Exchange
    include_symbols: str
    exclude_symbols: str

    Returns
    -------
    list[TradingPair]

    """
    if include_symbols is not None:
        include_symbols_list = include_symbols.split(',')

        return exchange.get_assets(include_symbols_list)

    else:
        all_assets = exchange.get_assets()

        if exclude_symbols is not None:
            exclude_symbols_list = exclude_symbols.split(',')

            assets = []
            for asset in all_assets:
                if asset.symbol not in exclude_symbols_list:
                    assets.append(asset)

            return assets

        else:
            return all_assets
