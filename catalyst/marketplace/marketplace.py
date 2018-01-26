import os
import sys
import json
import hmac
import glob
import time
import shutil
import hashlib

import bcolz
import logbook
import pandas as pd
import six
import requests
from web3 import Web3, HTTPProvider

from catalyst.constants import LOG_LEVEL
from catalyst.exchange.utils.stats_utils import set_print_settings
from catalyst.marketplace.marketplace_errors import (
    MarketplacePubAddressEmpty, MarketplaceDatasetNotFound,
    MarketplaceNoAddressMatch, MarketplaceHTTPRequest,
    MarketplaceNoCSVFiles)
from catalyst.marketplace.utils.bundle_utils import merge_bundles
from catalyst.marketplace.utils.path_utils import get_data_source, \
    get_bundle_folder, get_data_source_folder, get_marketplace_folder, \
    get_user_pubaddr
from catalyst.marketplace.utils.eth_utils import bytes32, b32_str
from catalyst.marketplace.utils.auth_utils import get_key_secret

if sys.version_info.major < 3:
    import urllib
else:
    import urllib.request as urllib

# TODO: host our own node on aws?
# TODO: switch to mainnet
REMOTE_NODE = 'https://ropsten.infura.io/'

# TODO: move to MASTER branch on github
CONTRACT_PATH = 'https://raw.githubusercontent.com/enigmampc/catalyst/' \
                'data-marketplace/catalyst/marketplace/contract_address.txt'

CONTRACT_ABI = 'https://raw.githubusercontent.com/enigmampc/catalyst/' \
               'data-marketplace/catalyst/marketplace/contract_abi.json'

AUTH_SERVER = 'http://localhost:5000'

log = logbook.Logger('Marketplace', level=LOG_LEVEL)


class Marketplace:
    def __init__(self):

        self.addresses = get_user_pubaddr()

        if self.addresses[0]['pubAddr'] == '':
            raise MarketplacePubAddressEmpty(
                    filename=os.path.join(
                        get_marketplace_folder(), 'addresses.json')
                    )
        self.default_account = self.addresses[0]['pubAddr']

        contract_url = urllib.urlopen(CONTRACT_PATH)
        self.contract_address = Web3.toChecksumAddress(
                                    contract_url.readline().strip())

        abi_url = urllib.urlopen(CONTRACT_ABI)
        abi = json.load(abi_url)

        self.web3 = Web3(HTTPProvider(REMOTE_NODE))

        self.contract = self.web3.eth.contract(
            self.contract_address,
            abi=abi,
        )

    def get_data_sources_map(self):
        return [
            dict(
                name='Marketcap',
                desc='The marketcap value in USD.',
                start_date=pd.to_datetime('2017-01-01'),
                end_date=pd.to_datetime('2018-01-15'),
                data_frequencies=['daily'],
            ),
            dict(
                name='GitHub',
                desc='The rate of development activity on GitHub.',
                start_date=pd.to_datetime('2017-01-01'),
                end_date=pd.to_datetime('2018-01-15'),
                data_frequencies=['daily', 'hour'],
            ),
            dict(
                name='Influencers',
                desc='Tweets and related sentiments by selected influencers.',
                start_date=pd.to_datetime('2017-01-01'),
                end_date=pd.to_datetime('2018-01-15'),
                data_frequencies=['daily', 'hour', 'minute'],
            ),
        ]

    def get_data_source_def(self, data_source_name):
        data_source_name = data_source_name.lower()
        dsm = self.get_data_sources_map()

        ds = six.next(
            (d for d in dsm if d['name'].lower() == data_source_name), None
        )
        return ds

    def list(self):
        subscribers = self.contract.call(
            {'from': self.default_account}
        ).getSubscribers()

        subscribed = []
        for index, address in enumerate(subscribers):
            if address == self.default_account:
                subscribed.append(index)

        data_sources = self.get_data_sources_map()

        data = []
        for index, data_source in enumerate(data_sources):
            data.append(
                dict(
                    id=index,
                    subscribed=index in subscribed,
                    **data_source
                )
            )

        df = pd.DataFrame(data)
        df.set_index(['id', 'name', 'desc'], drop=True, inplace=True)
        set_print_settings()

        formatters = dict(
            subscribed=lambda s: u'\u2713' if s else '',
        )
        print(df.to_string(formatters=formatters))

        pass

    def subscribe(self, dataset):
        data_sources = self.get_data_sources_map()
        index = next(
            (index for (index, d) in enumerate(data_sources) if
             d['name'].lower() == dataset.lower()),
            None
        )
        if index is None:
            raise ValueError(
                'Data source not found.'
            )

        try:
            self.contract.transact(
                {'from': self.default_account}
            ).subscribe(index)
            print(
                'Subscribed to data source {} successfully'.format(
                    dataset
                )
            )

        except Exception as e:
            print('Unable to subscribe to data source: {}'.format(e))

        pass

    def ingest(self, data_source_name, data_frequency=None, start=None,
               end=None, force_download=False):
        data_source_name = data_source_name.lower()

        period = start.strftime('%Y-%m-%d')
        tmp_folder = get_data_source(data_source_name, period, force_download)

        bundle_folder = get_bundle_folder(data_source_name, data_frequency)
        if os.listdir(bundle_folder):
            zsource = bcolz.ctable(rootdir=tmp_folder, mode='r')
            ztarget = bcolz.ctable(rootdir=bundle_folder, mode='r')
            merge_bundles(zsource, ztarget)

        else:
            os.rename(tmp_folder, bundle_folder)

        pass

    def get_data_source(self, data_source_name, data_frequency=None,
                        start=None, end=None):
        data_source_name = data_source_name.lower()

        if data_frequency is None:
            ds_def = self.get_data_source_def(data_source_name)
            freqs = ds_def['data_frequencies']
            data_frequency = freqs[0]

            if len(freqs) > 1:
                log.warn(
                    'no data frequencies specified for data source {}, '
                    'selected the first one by default: {}'.format(
                        data_source_name, data_frequency
                    )
                )

        # TODO: filter ctable by start and end date
        bundle_folder = get_bundle_folder(data_source_name, data_frequency)
        z = bcolz.ctable(rootdir=bundle_folder, mode='r')

        df = z.todataframe()  # type: pd.DataFrame
        df.set_index(['date', 'symbol'], drop=False, inplace=True)

        if start and end is None:
            df = df.xs(start, level=0)

        return df

    def clean(self, data_source_name, data_frequency=None):
        data_source_name = data_source_name.lower()

        if data_frequency is None:
            folder = get_data_source_folder(data_source_name)

        else:
            folder = get_bundle_folder(data_source_name, data_frequency)

        shutil.rmtree(folder)
        pass

    def register(self):
        dataset = input('Enter the name of the dataset to register: ')
        price = int(input('Enter the price for a monthly subscription to '
                          'this dataset in ENG: '))

        # while True:
        #     freq = input('Enter the data frequency [daily, hourly, minute]: ')
        #     if freq.lower() not in ('daily', 'houlry', 'minute'):
        #         print("Not a valid frequency.")
        #     else:
        #         break

        # while True:
        #     reg_pub = input('Can data be published every hour at a regular '
        #                     'time? [default: Y]: ') or 'y'
        #     if reg_pub.lower() not in ('y', 'n'):
        #         print("Please answer Y or N.")
        #     else:
        #         if reg_pub.lower() == 'y':
        #             reg_pub = True
        #         else:
        #             reg_pub = False
        #         break

        # while True:
        #     hist = input('Does it include historical data? '
        #                  '[default: Y]') or 'y'
        #     if hist.lower() not in ('y', 'n'):
        #         print("Please answer Y or N.")
        #     else:
        #         if hist.lower() == 'y':
        #             hist = True
        #         else:
        #             hist = False
        #         break

        while True:
            for i in range(0, len(self.addresses)):
                print('{}\t{}\t{}'.format(
                    i,
                    self.addresses[i]['pubAddr'],
                    self.addresses[i]['desc'])
                )
            address_i = int(input('Choose your address associated with '
                                  'this transaction: [default: 0] ') or 0)
            if not (0 <= address_i < len(self.addresses)):
                print('Please choose a number between 0 and {}\n'.format(
                        len(self.addresses)-1))
            else:
                address = Web3.toChecksumAddress(
                               self.addresses[address_i]['pubAddr'])
                break

        tx = self.contract.functions.register(
                    bytes32(dataset),
                    price,
                    address,
                 ).buildTransaction(
                    {'nonce': self.web3.eth.getTransactionCount(address)})

        tx['gas'] = int(tx['gas'] * 1.5)     # Defaults to not enough gas

        print('\nVisit https://www.myetherwallet.com/#offline-transaction and '
              'enter the following parameters:\n\n'
              'From Address:\t\t{_from}\n'
              'To Address:\t\t{to}\n'
              'Value / Amount to Send:\t{value}\n'
              'Gas Limit:\t\t{gas}\n'
              'Nonce:\t\t\t{nonce}\n'
              'Data:\t\t\t{data}\n'.format(
                    _from=address,
                    to=tx['to'],
                    value=tx['value'],
                    gas=tx['gas'],
                    nonce=tx['nonce'],
                    data=tx['data'],
                    )
              )

        signed_tx = input('Copy and Paste the "Signed Transaction" '
                          'field here:\n')

        tx_hash = '0x{}'.format(b32_str(
                    self.web3.eth.sendRawTransaction(signed_tx)))

        print('\nThis is the TxHash for this transaction: {}'.format(tx_hash))

    def publish(self, dataset, datadir, watch):

        datasource = self.contract.functions.getDataSource(
                        bytes32(dataset)).call()

        if not datasource[4]:
            raise MarketplaceDatasetNotFound(dataset=dataset)

        match = next((l for l in self.addresses if
                      l['pubAddr'] == datasource[0]), None)

        if not match:
            raise MarketplaceNoAddressMatch(
                    dataset=dataset,
                    address=datasource[0])

        print('Using address: {} to publish this dataset.'.format(
                datasource[0]))

        if 'key' in match:
            key = match['key']
            secret = match['secret']
        else:
            # TODO: Verify signature to obtain key/secret pair
            key, secret = get_key_secret(datasource[0], dataset)

        nonce = str(int(time.time()))

        signature = hmac.new(secret.encode('utf-8'),
                             nonce.encode('utf-8'),
                             hashlib.sha512).hexdigest()
        headers = {'Sign': signature, 'Key': key, 'Nonce': nonce}

        filenames = glob.glob(os.path.join(datadir, '*.csv'))

        if not filenames:
            raise MarketplaceNoCSVFiles(datadir=datadir)

        files = []
        for file in filenames:
            files.append(('file', open(file, 'rb')))

        r = requests.post('{}/publish'.format(AUTH_SERVER),
                          files=files,
                          headers=headers)

        if r.status_code != 200:
            raise MarketplaceHTTPRequest(request='upload file',
                                         error=r.status_code)

        if 'error' in r.json():
            raise MarketplaceHTTPRequest(request='upload file',
                                         error=r.json()['error'])

        print('Dataset {} published successfully.'.format(dataset))
