import os
import tempfile
from datetime import timedelta
from random import randint

import pandas as pd
from catalyst.assets._assets import TradingPair

from catalyst.utils.paths import ensure_directory


def rnd_history_date_days(max_days=30, last_dt=None):
    if last_dt is None:
        last_dt = pd.Timestamp.utcnow()

    days = randint(0, max_days)

    return last_dt - timedelta(days=days)


def rnd_history_date_minutes(max_minutes=1440):
    now = pd.Timestamp.utcnow()
    days = randint(0, max_minutes)

    return now - timedelta(minutes=days)


def rnd_bar_count(max_bars=21):
    # now = pd.Timestamp.utcnow()
    return randint(0, max_bars)


def output_df(df, assets, name=None):
    """
    Outputs a price DataFrame to a temp folder.

    Parameters
    ----------
    df: pd.DataFrame
    assets
    name

    Returns
    -------

    """
    if isinstance(assets, TradingPair):
        exchange_folder = assets.exchange
        asset_folder = assets.symbol
    else:
        exchange_folder = ','.join([asset.exchange for asset in assets])
        asset_folder = ','.join([asset.symbol for asset in assets])

    folder = os.path.join(
        tempfile.gettempdir(), 'catalyst', exchange_folder, asset_folder
    )
    ensure_directory(folder)

    if name is None:
        name = 'output'

    path = os.path.join(folder, '{}.csv'.format(name))
    df.to_csv(path)

    return path
