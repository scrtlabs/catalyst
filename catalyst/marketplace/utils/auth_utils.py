import hashlib
import hmac
import webbrowser

import requests
import time

from catalyst.marketplace.marketplace_errors import (
    MarketplaceHTTPRequest, MarketplaceWalletNotSupported,
    MarketplaceEmptySignature)
from catalyst.marketplace.utils.path_utils import (
    get_user_pubaddr, save_user_pubaddr)
from catalyst.constants import AUTH_SERVER, SUPPORTED_WALLETS


def get_key_secret(pubAddr, wallet):
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
                            'Authorization': 'Digest username="{0}"'.format(
                                pubAddr)})

    if response.status_code != 401:
        raise MarketplaceHTTPRequest(request=str('obtain key/secret'),
                                     error='Unexpected response code: '
                                           '{}'.format(response.status_code))

    header = response.headers.get('WWW-Authenticate')
    auth_type, auth_info = header.split(None, 1)
    d = requests.utils.parse_dict_header(auth_info)

    nonce = 'Catalyst nonce: 0x{}'.format(d['nonce'])

    if wallet in SUPPORTED_WALLETS:
        url = 'https://www.mycrypto.com/signmsg.html'

        print('\nObtaining a key/secret pair to streamline all future '
              'requests with the authentication server.\n'
              'Visit {url} and sign the '
              'following message (copy the entire line, without the '
              'line break at the end):\n\n{nonce}'.format(
                url=url,
                nonce=nonce))

        webbrowser.open_new(url)

        signature = input('\nCopy and Paste the "sig" field from '
                          'the signature here (without the double quotes, '
                          'only the HEX value):\n')
    else:
        raise MarketplaceWalletNotSupported(wallet=wallet)

    if signature is None:
        raise MarketplaceEmptySignature()

    signature = signature[2:]
    r = int(signature[0:64], base=16)
    s = int(signature[64:128], base=16)
    v = int(signature[128:130], base=16)
    vrs = [v, r, s]

    response = session.get('{}/marketplace/getkeysecret'.format(AUTH_SERVER),
                           headers={
                'Authorization': 'Digest username="{0}",realm="{1}",'
                'nonce="{2}",uri="/marketplace/getkeysecret",response="{3}",'
                'opaque="{4}"'.format(pubAddr,
                                      d['realm'],
                                      d['nonce'],
                                      ','.join(str(e) for e in vrs+[wallet]),
                                      d['opaque'])})

    if response.status_code == 200:

        if 'error' in response.json():
            raise MarketplaceHTTPRequest(request=str('obtain key/secret'),
                                         error=str(response.json()['error']))
        else:
            addresses = get_user_pubaddr()

            match = next((l for l in addresses if
                          l['pubAddr'].lower() == pubAddr.lower()), None)

            match['key'] = response.json()['key']
            match['secret'] = response.json()['secret']

            addresses[addresses.index(match)] = match

            save_user_pubaddr(addresses)
            print('Key/secret pair retrieved successfully from server.')

            return match['key'], match['secret']

    else:
        raise MarketplaceHTTPRequest(request=str('obtain key/secret'),
                                     error=response.status_code)


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
    nonce = str(int(time.time() * 1000))

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
