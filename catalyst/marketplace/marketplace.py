import json
import os
import shutil
import urllib

import bcolz
import logbook
import pandas as pd
import six
from web3 import Web3, HTTPProvider

from catalyst.constants import ROOT_DIR, LOG_LEVEL
from catalyst.exchange.utils.stats_utils import set_print_settings
from catalyst.marketplace.utils.bundle_utils import merge_bundles
from catalyst.marketplace.utils.path_utils import get_data_source, \
    get_bundle_folder, get_data_source_folder

# TODO: host our own node on aws?
# TODO: switch to mainnet
REMOTE_NODE = 'https://ropsten.infura.io/' 

# TODO: move to MASTER branch on github
CONTRACT_PATH = 'https://raw.githubusercontent.com/enigmampc/catalyst/' \
                'data-marketplace/catalyst/marketplace/contract_address.txt'

CONTRACT_ABI = 'https://raw.githubusercontent.com/enigmampc/catalyst/' \
               'data-marketplace/catalyst/marketplace/contract_abi.json'

log = logbook.Logger('Marketplace', level=LOG_LEVEL)


class Marketplace:
    def __init__(self):

        contract_url = urllib.urlopen(CONTRACT_PATH) 
        CONTRACT_ADDRESS = Web3.toChecksumAddress(
                                    contract_url.readline().strip())

        abi_url = urllib.urlopen(CONTRACT_ABI)
        abi = json.load(abi_url)

        w3 = Web3(HTTPProvider(REMOTE_NODE))

        self.contract = w3.eth.contract(
            CONTRACT_ADDRESS,
            abi=abi,
        )  # Type: Contract

        # TODO: Set default address correctly from user-provided config
        DEFAULT_ETH_ADDRESS = os.environ.get('DEFAULT_ETH_ADDRESS', None)
        if DEFAULT_ETH_ADDRESS is None:
            raise ValueError('DEFAULT_ETH_ADDRESS is not set. Export as an '
                             'environment variable. Quitting...')

        self.default_account = DEFAULT_ETH_ADDRESS
        pass

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

    def register(self, data_source_name):
        data_sources = self.get_data_sources_map()
        index = next(
            (index for (index, d) in enumerate(data_sources) if
             d['name'].lower() == data_source_name.lower()),
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
                    data_source_name
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
