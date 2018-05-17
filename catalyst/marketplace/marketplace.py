from __future__ import print_function

import glob
import json
import os
import re
import shutil
import sys
import time
import webbrowser

import bcolz
import logbook
import pandas as pd
import requests
from requests_toolbelt import MultipartDecoder
from requests_toolbelt.multipart.decoder import \
    NonMultipartContentTypeException

from catalyst.constants import (
    LOG_LEVEL, AUTH_SERVER, ETH_REMOTE_NODE, MARKETPLACE_CONTRACT,
    MARKETPLACE_CONTRACT_ABI, ENIGMA_CONTRACT, ENIGMA_CONTRACT_ABI)
from catalyst.exchange.utils.stats_utils import set_print_settings
from catalyst.marketplace.marketplace_errors import (
    MarketplacePubAddressEmpty, MarketplaceDatasetNotFound,
    MarketplaceNoAddressMatch, MarketplaceHTTPRequest,
    MarketplaceNoCSVFiles, MarketplaceRequiresPython3)
from catalyst.marketplace.utils.auth_utils import get_key_secret, \
    get_signed_headers
from catalyst.marketplace.utils.eth_utils import bin_hex, from_grains, \
    to_grains
from catalyst.marketplace.utils.path_utils import get_bundle_folder, \
    get_data_source_folder, get_marketplace_folder, \
    get_user_pubaddr, get_temp_bundles_folder, extract_bundle
from catalyst.utils.paths import ensure_directory

if sys.version_info.major < 3:
    import urllib
else:
    import urllib.request as urllib

log = logbook.Logger('Marketplace', level=LOG_LEVEL)


class Marketplace:
    def __init__(self):
        global Web3
        try:
            from web3 import Web3, HTTPProvider
        except ImportError:
            raise MarketplaceRequiresPython3()

        self.addresses = get_user_pubaddr()

        if self.addresses[0]['pubAddr'] == '':
            raise MarketplacePubAddressEmpty(
                filename=os.path.join(
                    get_marketplace_folder(), 'addresses.json')
            )
        self.default_account = self.addresses[0]['pubAddr']

        self.web3 = Web3(HTTPProvider(ETH_REMOTE_NODE))

        contract_url = urllib.urlopen(MARKETPLACE_CONTRACT)

        self.mkt_contract_address = Web3.toChecksumAddress(
            contract_url.readline().decode(
                contract_url.info().get_content_charset()).strip())

        abi_url = urllib.urlopen(MARKETPLACE_CONTRACT_ABI)
        abi_url = abi_url.read().decode(
                abi_url.info().get_content_charset())

        abi = json.loads(abi_url)

        self.mkt_contract = self.web3.eth.contract(
            self.mkt_contract_address,
            abi=abi,
        )

        contract_url = urllib.urlopen(ENIGMA_CONTRACT)

        self.eng_contract_address = Web3.toChecksumAddress(
            contract_url.readline().decode(
                contract_url.info().get_content_charset()).strip())

        abi_url = urllib.urlopen(ENIGMA_CONTRACT_ABI)
        abi_url = abi_url.read().decode(
                abi_url.info().get_content_charset())

        abi = json.loads(abi_url)

        self.eng_contract = self.web3.eth.contract(
            self.eng_contract_address,
            abi=abi,
        )

    # def get_data_sources_map(self):
    #     return [
    #         dict(
    #             name='Marketcap',
    #             desc='The marketcap value in USD.',
    #             start_date=pd.to_datetime('2017-01-01'),
    #             end_date=pd.to_datetime('2018-01-15'),
    #             data_frequencies=['daily'],
    #         ),
    #         dict(
    #             name='GitHub',
    #             desc='The rate of development activity on GitHub.',
    #             start_date=pd.to_datetime('2017-01-01'),
    #             end_date=pd.to_datetime('2018-01-15'),
    #             data_frequencies=['daily', 'hour'],
    #         ),
    #         dict(
    #             name='Influencers',
    #             desc='Tweets & related sentiments by selected influencers.',
    #             start_date=pd.to_datetime('2017-01-01'),
    #             end_date=pd.to_datetime('2018-01-15'),
    #             data_frequencies=['daily', 'hour', 'minute'],
    #         ),
    #     ]

    def to_text(self, hex):
        return Web3.toText(hex).rstrip('\0')

    def choose_pubaddr(self):
        if len(self.addresses) == 1:
            address = self.addresses[0]['pubAddr']
            address_i = 0
            print('Using {} for this transaction.'.format(address))
        else:
            while True:
                for i in range(0, len(self.addresses)):
                    print('{}\t{}\t{}\t{}'.format(
                        i,
                        self.addresses[i]['pubAddr'],
                        self.addresses[i]['wallet'].ljust(10),
                        self.addresses[i]['desc'])
                    )
                address_i = int(input('Choose your address associated with '
                                      'this transaction: [default: 0] ') or 0)
                if not (0 <= address_i < len(self.addresses)):
                    print('Please choose a number between 0 and {}\n'.format(
                        len(self.addresses) - 1))
                else:
                    address = Web3.toChecksumAddress(
                        self.addresses[address_i]['pubAddr'])
                    break

        return address, address_i

    def sign_transaction(self, tx):

        url = 'https://www.mycrypto.com/#offline-transaction'
        print('\nVisit {url} and enter the following parameters:\n\n'
              'From Address:\t\t{_from}\n'
              '\n\tClick the "Generate Information" button\n\n'
              'To Address:\t\t{to}\n'
              'Value / Amount to Send:\t{value}\n'
              'Gas Limit:\t\t{gas}\n'
              'Gas Price:\t\t[Accept the default value]\n'
              'Nonce:\t\t\t{nonce}\n'
              'Data:\t\t\t{data}\n'.format(
                url=url,
                _from=tx['from'],
                to=tx['to'],
                value=tx['value'],
                gas=tx['gas'],
                nonce=tx['nonce'],
                data=tx['data'], )
              )

        webbrowser.open_new(url)

        signed_tx = input('Copy and Paste the "Signed Transaction" '
                          'field here:\n')

        if signed_tx.startswith('0x'):
            signed_tx = signed_tx[2:]

        return signed_tx

    def check_transaction(self, tx_hash):

        if 'ropsten' in ETH_REMOTE_NODE:
            etherscan = 'https://ropsten.etherscan.io/tx/'
        elif 'rinkeby' in ETH_REMOTE_NODE:
            etherscan = 'https://rinkeby.etherscan.io/tx/'
        else:
            etherscan = 'https://etherscan.io/tx/'
        etherscan = '{}{}'.format(etherscan, tx_hash)

        print('\nYou can check the outcome of your transaction here:\n'
              '{}\n\n'.format(etherscan))

    def _list(self):
        num_data_sources = self.mkt_contract.functions.getProviderNamesSize().call()
        data_sources = [self.mkt_contract.functions.getNameAt(x).call() for x in range(num_data_sources)]

        data = []
        for index, data_source in enumerate(data_sources):
            if index >= 0:
                if 'test' not in Web3.toText(data_source).lower():
                    data.append(
                        dict(
                            dataset=self.to_text(data_source)
                        )
                    )
        return pd.DataFrame(data)

    def list(self):
        df = self._list()

        set_print_settings()
        if df.empty:
            print('There are no datasets available yet.')
        else:
            print(df)

    def subscribe(self, dataset=None):

        if dataset is None:

            df_sets = self._list()
            if df_sets.empty:
                print('There are no datasets available yet.')
                return

            set_print_settings()
            while True:
                print(df_sets)
                dataset_num = input('Choose the dataset you want to '
                                    'subscribe to [0..{}]: '.format(
                                        df_sets.size - 1))
                try:
                    dataset_num = int(dataset_num)
                except ValueError:
                    print('Enter a number between 0 and {}'.format(
                        df_sets.size - 1))
                else:
                    if dataset_num not in range(0, df_sets.size):
                        print('Enter a number between 0 and {}'.format(
                            df_sets.size - 1))
                    else:
                        dataset = df_sets.iloc[dataset_num]['dataset']
                        break

        dataset = dataset.lower()

        address = self.choose_pubaddr()[0]
        provider_info = self.mkt_contract.functions.getDataProviderInfo(
            Web3.toHex(dataset)
        ).call()

        if not provider_info[4]:
            print('The requested "{}" dataset is not registered in '
                  'the Data Marketplace.'.format(dataset))
            return

        grains = provider_info[1]
        price = from_grains(grains)

        subscribed = self.mkt_contract.functions.checkAddressSubscription(
            address, Web3.toHex(dataset)
        ).call()

        if subscribed[5]:
            print(
                '\nYou are already subscribed to the "{}" dataset.\n'
                'Your subscription started on {} UTC, and is valid until '
                '{} UTC.'.format(
                    dataset,
                    pd.to_datetime(subscribed[3], unit='s', utc=True),
                    pd.to_datetime(subscribed[4], unit='s', utc=True)
                )
            )
            return

        print('\nThe price for a monthly subscription to this dataset is'
              ' {} ENG'.format(price))

        print(
            'Checking that the ENG balance in {} is greater than {} '
            'ENG... '.format(address, price), end=''
        )

        wallet_address = address[2:]
        balance = self.web3.eth.call({
            'from': address,
            'to': self.eng_contract_address,
            'data': '0x70a08231000000000000000000000000{}'.format(
                wallet_address
            )
        })

        try:
            balance = Web3.toInt(balance)  # web3 >= 4.0.0b7
        except TypeError:
            balance = Web3.toInt(hexstr=balance)  # web3 <= 4.0.0b6

        if balance > grains:
            print('OK.')
        else:
            print('FAIL.\n\nAddress {} balance is {} ENG,\nwhich is lower '
                  'than the price of the dataset that you are trying to\n'
                  'buy: {} ENG. Get enough ENG to cover the costs of the '
                  'monthly\nsubscription for what you are trying to buy, '
                  'and try again.'.format(
                    address, from_grains(balance), price))
            return

        while True:
            agree_pay = input('Please confirm that you agree to pay {} ENG '
                              'for a monthly subscription to the dataset "{}" '
                              'starting today. [default: Y] '.format(
                                price, dataset)) or 'y'
            if agree_pay.lower() not in ('y', 'n'):
                print("Please answer Y or N.")
            else:
                if agree_pay.lower() == 'y':
                    break
                else:
                    return

        print('Ready to subscribe to dataset {}.\n'.format(dataset))
        print('In order to execute the subscription, you will need to sign '
              'two different transactions:\n'
              '1. First transaction is to authorize the Marketplace contract '
              'to spend {} ENG on your behalf.\n'
              '2. Second transaction is the actual subscription for the '
              'desired dataset'.format(price))

        tx = self.eng_contract.functions.approve(
            self.mkt_contract_address,
            grains,
        ).buildTransaction(
            {'from': address,
             'nonce': self.web3.eth.getTransactionCount(address)}
        )

        signed_tx = self.sign_transaction(tx)
        try:
            tx_hash = '0x{}'.format(
                bin_hex(self.web3.eth.sendRawTransaction(signed_tx))
            )
            print(
                '\nThis is the TxHash for this transaction: {}'.format(tx_hash)
            )

        except Exception as e:
            print('Unable to subscribe to data source: {}'.format(e))
            return

        self.check_transaction(tx_hash)

        print('Waiting for the first transaction to succeed...')

        while True:
            try:
                if self.web3.eth.getTransactionReceipt(tx_hash).status:
                    break
                else:
                    print('\nTransaction failed. Aborting...')
                    return
            except AttributeError:
                pass
            for i in range(0, 10):
                print('.', end='', flush=True)
                time.sleep(1)

        print('\nFirst transaction successful!\n'
              'Now processing second transaction.')

        tx = self.mkt_contract.functions.subscribe(
            Web3.toHex(dataset),
        ).buildTransaction({
            'from': address,
            'nonce': self.web3.eth.getTransactionCount(address)})

        signed_tx = self.sign_transaction(tx)

        try:
            tx_hash = '0x{}'.format(bin_hex(
                self.web3.eth.sendRawTransaction(signed_tx)))
            print('\nThis is the TxHash for this transaction: '
                  '{}'.format(tx_hash))

        except Exception as e:
            print('Unable to subscribe to data source: {}'.format(e))
            return

        self.check_transaction(tx_hash)

        print('Waiting for the second transaction to succeed...')

        while True:
            try:
                if self.web3.eth.getTransactionReceipt(tx_hash).status:
                    break
                else:
                    print('\nTransaction failed. Aborting...')
                    return
            except AttributeError:
                pass
            for i in range(0, 10):
                print('.', end='', flush=True)
                time.sleep(1)

        print('\nSecond transaction successful!\n'
              'You have successfully subscribed to dataset {} with'
              'address {}.\n'
              'You can now ingest this dataset anytime during the '
              'next month by running the following command:\n'
              'catalyst marketplace ingest --dataset={}'.format(
                dataset, address, dataset))

    def process_temp_bundle(self, ds_name, path):
        """
        Merge the temp bundle into the main bundle for the specified
        data source.

        Parameters
        ----------
        ds_name
        path

        Returns
        -------

        """
        tmp_bundle = extract_bundle(path)
        bundle_folder = get_data_source_folder(ds_name)
        ensure_directory(bundle_folder)
        if os.listdir(bundle_folder):
            zsource = bcolz.ctable(rootdir=tmp_bundle, mode='r')
            ztarget = bcolz.ctable(rootdir=bundle_folder, mode='a')
            ztarget.append(zsource)

        else:
            shutil.rmtree(bundle_folder, ignore_errors=True)
            os.rename(tmp_bundle, bundle_folder)

    def ingest(self, ds_name=None, start=None, end=None, force_download=False):

        if ds_name is None:

            df_sets = self._list()
            if df_sets.empty:
                print('There are no datasets available yet.')
                return

            set_print_settings()
            while True:
                print(df_sets)
                dataset_num = input('Choose the dataset you want to '
                                    'ingest [0..{}]: '.format(
                                        df_sets.size - 1))
                try:
                    dataset_num = int(dataset_num)
                except ValueError:
                    print('Enter a number between 0 and {}'.format(
                        df_sets.size - 1))
                else:
                    if dataset_num not in range(0, df_sets.size):
                        print('Enter a number between 0 and {}'.format(
                            df_sets.size - 1))
                    else:
                        ds_name = df_sets.iloc[dataset_num]['dataset']
                        break

        # ds_name = ds_name.lower()

        # TODO: catch error conditions
        provider_info = self.mkt_contract.functions.getDataProviderInfo(
            Web3.toHex(ds_name)
        ).call()

        if not provider_info[4]:
            print('The requested "{}" dataset is not registered in '
                  'the Data Marketplace.'.format(ds_name))
            return

        address, address_i = self.choose_pubaddr()
        fns = self.mkt_contract.functions
        check_sub = fns.checkAddressSubscription(
            address, Web3.toHex(ds_name)
        ).call()

        if check_sub[0] != address or self.to_text(check_sub[1]) != ds_name:
            print('You are not subscribed to dataset "{}" with address {}. '
                  'Plese subscribe first.'.format(ds_name, address))
            return

        if not check_sub[5]:
            print('Your subscription to dataset "{}" expired on {} UTC.'
                  'Please renew your subscription by running:\n'
                  'catalyst marketplace subscribe --dataset={}'.format(
                    ds_name,
                    pd.to_datetime(check_sub[4], unit='s', utc=True),
                    ds_name)
                  )

        if 'key' in self.addresses[address_i]:
            key = self.addresses[address_i]['key']
            secret = self.addresses[address_i]['secret']
        else:
            key, secret = get_key_secret(address,
                                         self.addresses[address_i]['wallet'])

        headers = get_signed_headers(ds_name, key, secret)
        log.info('Starting download of dataset for ingestion...')
        r = requests.post(
            '{}/marketplace/ingest'.format(AUTH_SERVER),
            headers=headers,
            stream=True,
        )
        if r.status_code == 200:
            log.info('Dataset downloaded successfully. Processing dataset...')
            bundle_folder = get_data_source_folder(ds_name)
            shutil.rmtree(bundle_folder, ignore_errors=True)
            target_path = get_temp_bundles_folder()
            try:
                decoder = MultipartDecoder.from_response(r)
                # with maybe_show_progress(
                #     iter(decoder.parts),
                #     True,
                #     label='Processing files') as part:
                counter = 1
                for part in decoder.parts:
                    log.info("Processing file {} of {}".format(
                        counter, len(decoder.parts)))
                    h = part.headers[b'Content-Disposition'].decode('utf-8')
                    # Extracting the filename from the header
                    name = re.search(r'filename="(.*)"', h).group(1)

                    filename = os.path.join(target_path, name)
                    with open(filename, 'wb') as f:
                        # for chunk in part.content.iter_content(
                        #         chunk_size=1024):
                        #     if chunk: # filter out keep-alive new chunks
                        #         f.write(chunk)
                        f.write(part.content)

                    self.process_temp_bundle(ds_name, filename)
                    counter += 1

            except NonMultipartContentTypeException:
                response = r.json()
                raise MarketplaceHTTPRequest(
                    request='ingest dataset',
                    error=response,
                )
        else:
            raise MarketplaceHTTPRequest(
                request='ingest dataset',
                error=r.status_code,
            )

        log.info('{} ingested successfully'.format(ds_name))

    def get_dataset(self, ds_name, start=None, end=None):
        ds_name = ds_name.lower()

        # TODO: filter ctable by start and end date
        bundle_folder = get_data_source_folder(ds_name)
        z = bcolz.ctable(rootdir=bundle_folder, mode='r')

        # if start is not None and end is not None:
        #     z = z.fetchwhere('(date>=start_date) & (date<end_date)', user_dict={'start_date': start.to_datetime64(),
        #                                                                          'end_date': end.to_datetime64()})
        # elif start is not None:
        #     z = z.fetchwhere('(date>=start_date)', user_dict={'start_date': start.to_datetime64()})
        # elif end is not None:
        #     z = z.fetchwhere('(date<end_date)', user_dict={'end_date': end.to_datetime64()})
        df = z.todataframe()  # type: pd.DataFrame
        df.set_index(['date', 'symbol'], drop=True, inplace=True)

        # TODO: implement the filter more carefully
        # if start and end is None:
        #     df = df.xs(start, level=0)

        return df

    def clean(self, ds_name=None, data_frequency=None):

        if ds_name is None:
            mktplace_root = get_marketplace_folder()
            folders = [os.path.basename(f.rstrip('/'))
                       for f in glob.glob('{}/*/'.format(mktplace_root))
                       if 'temp_bundles' not in f]

            while True:
                for idx, f in enumerate(folders):
                    print('{}\t{}'.format(idx, f))
                dataset_num = input('Choose the dataset you want to '
                                    'clean [0..{}]: '.format(
                                        len(folders) - 1))
                try:
                    dataset_num = int(dataset_num)
                except ValueError:
                    print('Enter a number between 0 and {}'.format(
                        len(folders) - 1))
                else:
                    if dataset_num not in range(0, len(folders)):
                        print('Enter a number between 0 and {}'.format(
                            len(folders) - 1))
                    else:
                        ds_name = folders[dataset_num]
                        break

        ds_name = ds_name.lower()

        if data_frequency is None:
            folder = get_data_source_folder(ds_name)

        else:
            folder = get_bundle_folder(ds_name, data_frequency)

        shutil.rmtree(folder)

    def create_metadata(self, key, secret, ds_name, data_frequency, desc,
                        has_history=True, has_live=True):
        """

        Returns
        -------

        """
        headers = get_signed_headers(ds_name, key, secret)
        r = requests.post(
            '{}/marketplace/register'.format(AUTH_SERVER),
            json=dict(
                ds_name=ds_name,
                desc=desc,
                data_frequency=data_frequency,
                has_history=has_history,
                has_live=has_live,
            ),
            headers=headers,
        )

        if r.status_code != 200:
            raise MarketplaceHTTPRequest(
                request='register', error=r.status_code
            )

        if 'error' in r.json():
            raise MarketplaceHTTPRequest(
                request='upload file', error=r.json()['error']
            )

    def register(self):
        while True:
            desc = input('Enter the name of the dataset to register: ')
            dataset = desc.lower().strip()
            provider_info = self.mkt_contract.functions.getDataProviderInfo(
                Web3.toHex(dataset)
            ).call()

            if provider_info[4]:
                print('There is already a dataset registered under '
                      'the name "{}". Please choose a different '
                      'name.'.format(dataset))
            else:
                break

        price = int(
            input(
                'Enter the price for a monthly subscription to '
                'this dataset in ENG: '
            )
        )
        while True:
            freq = input('Enter the data frequency [daily, hourly, minute]: ')
            if freq.lower() not in ('daily', 'hourly', 'minute'):
                print('Not a valid frequency.')
            else:
                break

        while True:
            reg_pub = input(
                'Does it include historical data? [default: Y]: '
            ) or 'y'
            if reg_pub.lower() not in ('y', 'n'):
                print('Please answer Y or N.')
            else:
                if reg_pub.lower() == 'y':
                    has_history = True
                else:
                    has_history = False
                break

        while True:
            reg_pub = input(
                'Doest it include live data? [default: Y]: '
            ) or 'y'
            if reg_pub.lower() not in ('y', 'n'):
                print('Please answer Y or N.')
            else:
                if reg_pub.lower() == 'y':
                    has_live = True
                else:
                    has_live = False
                break

        address, address_i = self.choose_pubaddr()
        if 'key' in self.addresses[address_i]:
            key = self.addresses[address_i]['key']
            secret = self.addresses[address_i]['secret']
        else:
            key, secret = get_key_secret(address,
                                         self.addresses[address_i]['wallet'])

        grains = to_grains(price)

        tx = self.mkt_contract.functions.register(
            Web3.toHex(dataset),
            grains,
            address,
        ).buildTransaction(
            {'from': address,
             'nonce': self.web3.eth.getTransactionCount(address)}
        )

        signed_tx = self.sign_transaction(tx)

        try:
            tx_hash = '0x{}'.format(
                bin_hex(self.web3.eth.sendRawTransaction(signed_tx))
            )
            print(
                '\nThis is the TxHash for this transaction: {}'.format(tx_hash)
            )

        except Exception as e:
            print('Unable to register the requested dataset: {}'.format(e))
            return

        self.check_transaction(tx_hash)

        print('Waiting for the transaction to succeed...')

        while True:
            try:
                if self.web3.eth.getTransactionReceipt(tx_hash).status:
                    break
                else:
                    print('\nTransaction failed. Aborting...')
                    return
            except AttributeError:
                pass
            for i in range(0, 10):
                print('.', end='', flush=True)
                time.sleep(1)

        print('\nWarming up the {} dataset'.format(dataset))
        self.create_metadata(
            key=key,
            secret=secret,
            ds_name=dataset,
            data_frequency=freq,
            desc=desc,
            has_history=has_history,
            has_live=has_live,
        )
        print('\n{} registered successfully'.format(dataset))

    def publish(self, dataset, datadir, watch):
        dataset = dataset.lower()
        provider_info = self.mkt_contract.functions.getDataProviderInfo(
            Web3.toHex(dataset)
        ).call()

        if not provider_info[4]:
            raise MarketplaceDatasetNotFound(dataset=dataset)

        match = next(
            (l for l in self.addresses if l['pubAddr'] == provider_info[0]),
            None
        )
        if not match:
            raise MarketplaceNoAddressMatch(
                dataset=dataset,
                address=provider_info[0])

        print('Using address: {} to publish this dataset.'.format(
            provider_info[0]))

        if 'key' in match:
            key = match['key']
            secret = match['secret']
        else:
            key, secret = get_key_secret(provider_info[0], match['wallet'])

        filenames = glob.glob(os.path.join(datadir, '*.csv'))

        if not filenames:
            raise MarketplaceNoCSVFiles(datadir=datadir)

        def read_file(pathname):
            with open(pathname, 'rb') as f:
                return f.read()

        files = []
        for idx, file in enumerate(filenames):
            log.info('Uploading file {} of {}: {}'.format(
                idx+1, len(filenames), file))
            files.append(('file', (os.path.basename(file), read_file(file))))

        headers = get_signed_headers(dataset, key, secret)
        r = requests.post('{}/marketplace/publish'.format(AUTH_SERVER),
                          files=files,
                          headers=headers)

        if r.status_code != 200:
            raise MarketplaceHTTPRequest(request='upload file',
                                         error=r.status_code)

        if 'error' in r.json():
            raise MarketplaceHTTPRequest(request='upload file',
                                         error=r.json()['error'])

        log.info('File processed successfully.')

        print('\nDataset {} uploaded and processed successfully.'.format(
            dataset))
