import os
import random
import tempfile

from catalyst.assets._assets import TradingPair
from catalyst.exchange.utils.exchange_utils import get_exchange_folder
from catalyst.exchange.utils.factory import find_exchanges
from catalyst.utils.paths import ensure_directory


def handle_exchange_error(exchange, e):
    try:
        message = '{}: {}'.format(
            e.__class__, e.message.decode('ascii', 'ignore')
        )
    except Exception:
        message = 'unexpected error'

    folder = get_exchange_folder(exchange.name)
    filename = os.path.join(folder, 'blacklist.txt')
    with open(filename, 'wt') as handle:
        handle.write(message)


def select_random_exchanges(population=3, features=None,
                            is_authenticated=False, base_currency=None):
    all_exchanges = find_exchanges(
        features=features,
        is_authenticated=is_authenticated,
        base_currency=base_currency,
    )

    if population is not None:
        if len(all_exchanges) < population:
            population = len(all_exchanges)

        exchanges = random.sample(all_exchanges, population)

    else:
        exchanges = all_exchanges

    return exchanges


def select_random_assets(all_assets, population=3):
    assets = random.sample(all_assets, population)
    return assets


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
