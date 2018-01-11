import json
import os
import pandas as pd

from web3 import Web3, HTTPProvider

from catalyst.exchange.utils.stats_utils import set_print_settings
from catalyst.constants import ROOT_DIR
from catalyst.marketplace.utils.paths import get_temp_bundles_folder

REMOTE_NODE = 'http://localhost:7545'
CONTRACT_PATH = os.path.join(
    ROOT_DIR, '..', 'marketplace', 'build', 'contracts', 'Marketplace.json'
)
CONTRACT_ADDRESS = Web3.toChecksumAddress(
    '0xe2b6cf3863240892d59664d209a28289a73ef644'
)


class Marketplace:
    def __init__(self):
        with open(CONTRACT_PATH) as handle:
            json_interface = json.load(handle)
            w3 = Web3(HTTPProvider(REMOTE_NODE))

            self.contract = w3.eth.contract(
                CONTRACT_ADDRESS,
                abi=json_interface['abi'],
            )  # Type: Contract
            self.default_account = w3.eth.accounts[1]

            pass

    def get_data_sources_map(self):
        return [
            dict(
                name='Marketcap',
                desc='The marketcap value in USD.',
                start_date=pd.to_datetime('2017-01-01'),
                end_date=pd.to_datetime('2018-01-15'),
            ),
            dict(
                name='GitHub',
                desc='The rate of development activity on GitHub.',
                start_date=pd.to_datetime('2017-01-01'),
                end_date=pd.to_datetime('2018-01-15'),
            ),
            dict(
                name='Influencers',
                desc='Tweets and related sentiments by selected influencers.',
                start_date=pd.to_datetime('2017-01-01'),
                end_date=pd.to_datetime('2018-01-15'),
            ),
        ]

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
                    **data_source,
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
               end=None):
        temp_folder = get_temp_bundles_folder(data_source_name)
        pass

    def clean(self, data_source_name):
        pass
