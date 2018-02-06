import hashlib
import hmac

import requests
import time

from catalyst.marketplace.marketplace_errors import (
    MarketplaceHTTPRequest)
from catalyst.marketplace.utils.path_utils import (
    get_user_pubaddr, save_user_pubaddr)
from catalyst.constants import AUTH_SERVER


def get_key_secret(pubAddr, dataset):
    """
    Obtain a new key/secret pair from authentication server

    Parameters
    ----------
    pubAddr: str
    dataset: str

    Returns
    -------
    key: str
    secret: str

    """
    session = requests.Session()
    response = session.get('{}/marketplace/getkeysecret'.format(AUTH_SERVER),
                           headers={
                               'pubAddr': pubAddr,
                               'dataset': dataset})

    if 'error' in response.json():
        raise MarketplaceHTTPRequest(request=str('obtain key/secret'),
                                     error=str(response.json()['error']))

    addresses = get_user_pubaddr()

    match = next((l for l in addresses if
                  l['pubAddr'] == pubAddr), None)
    match['key'] = response.json()['key']
    match['secret'] = response.json()['secret']

    addresses[addresses.index(match)] = match

    save_user_pubaddr(addresses)

    return match['key'], match['secret']


def get_signed_headers(ds_name, key, secret):
    """
    Return a new request header including the key / secret signature

    Parameters
    ----------
    ds_name
    key
    secret

    Returns
    -------

    """
    nonce = str(int(time.time()))

    signature = hmac.new(
        secret.encode('utf-8'),
        '{}{}'.format(ds_name, nonce).encode('utf-8'),
        hashlib.sha512
    ).hexdigest()

    headers = {
        'Sign': signature,
        'Key': key,
        'Nonce': nonce,
        'Dataset': ds_name,
    }

    return headers
