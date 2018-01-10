import json
import os

from web3 import Web3, HTTPProvider

CONTRACT_PATH = os.path.join(
    '..', '..', 'marketplace', 'build', 'contracts', 'Marketplace.json'
)
CONTRACT_ADDRESS = Web3.toChecksumAddress(
    '0x345ca3e014aaf5dca488057592ee47305d9b3e10'
)


# we'll use one of our default accounts to deploy from. every write to the chain requires a
# payment of ethereum called "gas". if we were running an actual test ethereum node locally,
# then we'd have to go on the test net and get some free ethereum to play with. that is beyond
# the scope of this tutorial so we're using a mini local node that has unlimited ethereum and
# the only chain we're using is our own local one


class Marketplace:
    def __init__(self):
        with open(CONTRACT_PATH) as handle:
            json_interface = json.load(handle)

            w3 = Web3(HTTPProvider('http://localhost:7545'))

            self.contract = w3.eth.contract(
                CONTRACT_ADDRESS,
                abi=json_interface['abi'],
            )  # Type: Contract
            self.default_account = w3.eth.accounts[1]

            pass

    def list(self):
        subscribers = self.contract.call(
            {'from': self.default_account}
        ).getSubscribers()
        pass

    def register(self, data_source_name):
        test = self.contract.transact(
            {'from': self.default_account}
        ).subscribe(0)
        pass

    def ingest(self, data_source_name, data_frequency, start, end):
        pass

    def clean(self, data_source_name):
        pass
