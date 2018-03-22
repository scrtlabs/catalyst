import os
import json
import tarfile

from catalyst.constants import SUPPORTED_WALLETS
from catalyst.utils.deprecate import deprecated
from catalyst.utils.paths import data_root, ensure_directory
from catalyst.marketplace.marketplace_errors import MarketplaceJSONError


def get_marketplace_folder(environ=None):
    """
    The root path of the marketplace folder.

    Parameters
    ----------
    environ:

    Returns
    -------
    str

    """
    if not environ:
        environ = os.environ

    root = data_root(environ)
    marketplace_folder = os.path.join(root, 'marketplace')
    ensure_directory(marketplace_folder)

    return marketplace_folder


def get_data_source_folder(data_source_name, environ=None):
    """
    The root path of an data_source folder.

    Parameters
    ----------
    data_source_name: str
    environ:

    Returns
    -------
    str

    """
    if not environ:
        environ = os.environ

    root = data_root(environ)
    data_source_folder = os.path.join(root, 'marketplace', data_source_name)
    ensure_directory(data_source_folder)

    return data_source_folder


@deprecated
def get_bundle_folder(data_source_name, data_frequency, environ=None):
    data_source_folder = get_data_source_folder(data_source_name, environ)

    bundle_folder = os.path.join(data_source_folder, data_frequency)

    ensure_directory(bundle_folder)

    return bundle_folder


def get_temp_bundles_folder(environ=None):
    """
    The temp folder for bundle downloads by algo name.

    Parameters
    ----------
    ds_name: str
    environ:

    Returns
    -------
    str

    """
    root = data_root(environ)
    folder = os.path.join(root, 'marketplace', 'temp_bundles')
    ensure_directory(folder)

    return folder


def extract_bundle(tar_filename):
    """
    Extract a bcolz bundle.

    Parameters
    ----------
    ds_name

    Returns
    -------
    str

    """
    target_path = tar_filename.replace('.tar.gz', '')
    with tarfile.open(tar_filename, 'r') as tar:
        tar.extractall(target_path)

    return target_path


def get_user_pubaddr(environ=None):
    """
    The de-serialized contend of the user's addresses.json file.

    Parameters
    ----------
    environ:

    Returns
    -------
    Object

    """
    marketplace_folder = get_marketplace_folder(environ)
    filename = os.path.join(marketplace_folder, 'addresses.json')

    if os.path.isfile(filename):
        with open(filename) as data_file:
            try:
                data = json.load(data_file)
            except json.decoder.JSONDecodeError as e:
                raise MarketplaceJSONError(file=filename, error=e)
            try:
                d = data[0]['pubAddr']
            except Exception as e:
                data = [data, ]

            changed = False

            for idx, d in enumerate(data):
                try:
                    if d['wallet'] not in SUPPORTED_WALLETS:
                        data[idx]['wallet'] = _choose_wallet(
                            d['pubAddr'], False)
                        changed = True
                except KeyError:
                    data[idx]['wallet'] = _choose_wallet(
                        d['pubAddr'], True)
                    changed = True

            if changed:
                save_user_pubaddr(data)

            return data

    else:
        data = []
        data.append(dict(pubAddr='', desc='', wallet=''))
        with open(filename, 'w') as f:
            json.dump(data, f, sort_keys=False, indent=2,
                      separators=(',', ':'))
            return data


def _choose_wallet(pubAddr, missing):
    while True:
        if missing:
            print('\nYou need to specify a wallet for address '
                  '{}.'.format(pubAddr))
        else:
            print('\nThe wallet specified for address {} is not '
                  'supported.'.format(pubAddr))

        print('Please choose among the following options:')
        for idx, wallet in enumerate(SUPPORTED_WALLETS):
            print('{}\t{}'.format(idx, wallet))

        lw = len(SUPPORTED_WALLETS)-1
        w = input('Choose a number between 0 and {}: '.format(
                    lw))
        try:
            w = int(w)
        except ValueError:
            print('Enter a number between 0 and {}'.format(lw))
        else:
            if w not in range(0, lw+1):
                print('Enter a number between 0 and '
                      '{}'.format(lw))
            else:
                return SUPPORTED_WALLETS[w]


def save_user_pubaddr(data, environ=None):
    """
    Saves the user's public addresses and their related metadata in
    the corresponding addresses.json file.

    Parameters
    ----------
    data: dict

    Returns
    -------
    True

    """
    marketplace_folder = get_marketplace_folder(environ)
    filename = os.path.join(marketplace_folder, 'addresses.json')

    with open(filename, 'w') as f:
        json.dump(data, f, sort_keys=False, indent=2,
                  separators=(',', ':'))

    return True
