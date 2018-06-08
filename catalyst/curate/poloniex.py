import csv
import json
import os
import shutil
import time
from datetime import datetime

import logbook
import pandas as pd
import requests

from catalyst.exchange.utils.exchange_utils import \
    get_exchange_symbols_filename

DT_START = int(time.mktime(datetime(2010, 1, 1, 0, 0).timetuple()))
DT_END = pd.to_datetime('today').value // 10 ** 9
CSV_OUT_FOLDER = os.environ.get('CSV_OUT_FOLDER', '/efs/exchanges/poloniex/')
CONN_RETRIES = 2

logbook.StderrHandler().push_application()
log = logbook.Logger(__name__)


class PoloniexCurator(object):
    '''
    OHLCV data feed generator for crypto data. Based on Poloniex market data
    '''

    _api_path = 'https://poloniex.com/public?'
    currency_pairs = []

    def __init__(self):
        if not os.path.exists(CSV_OUT_FOLDER):
            try:
                os.makedirs(CSV_OUT_FOLDER)
            except Exception as e:
                log.error('Failed to create data folder: {}'.format(
                            CSV_OUT_FOLDER))
                log.exception(e)

    def get_currency_pairs(self):
        '''
        Retrieves and returns all currency pairs from the exchange
        '''
        url = self._api_path + 'command=returnTicker'

        try:
            response = requests.get(url)
        except Exception as e:
            log.error('Failed to retrieve list of currency pairs')
            log.exception(e)
            return None

        data = response.json()
        self.currency_pairs = []
        for ticker in data:
            self.currency_pairs.append(ticker)
        self.currency_pairs.sort()

        log.debug('Currency pairs retrieved successfully: {}'.format(
                    len(self.currency_pairs)
                    ))

    def _retrieve_tradeID_date(self, row):
        '''
        Helper function that reads tradeID and date fields from CSV readline
        '''
        tId = int(row.split(',')[0])
        d = pd.to_datetime(row.split(',')[1],
                           infer_datetime_format=True).value // 10 ** 9
        return tId, d

    def retrieve_trade_history(self, currencyPair, start=DT_START,
                               end=DT_END, temp=None):
        '''
        Retrieves TradeHistory from exchange for a given currencyPair
        between start and end dates. If no start date is provided, uses
        a system-wide one (beginning of time for cryptotrading).
        If no end date is provided, 'now' is used.

        Stores results in CSV file on disk.

        This function is called recursively to work around the
        limitations imposed by the provider API.
        '''
        csv_fn = CSV_OUT_FOLDER + 'crypto_trades-' + currencyPair + '.csv'

        '''
        Check what data we already have on disk, reading first and last
        lines from file. Data is stored on file from NEWEST to OLDEST.
        '''
        try:
            with open(csv_fn, 'ab+') as f:
                f.seek(0, os.SEEK_END)
                if(f.tell() > 2):                   # Check file size is not 0
                    f.seek(0)                       # Go to start to read
                    last_tradeID, end_file = self._retrieve_tradeID_date(
                                                    f.readline())
                    f.seek(-2, os.SEEK_END)         # Jump to the 2nd last byte
                    while f.read(1) != b"\n":       # Until EOL is found...
                        # ...jump back the read byte plus one more.
                        f.seek(-2, os.SEEK_CUR)
                    first_tradeID, start_file = self._retrieve_tradeID_date(
                                                    f.readline())

                    if(end_file + 3600 * 6 > DT_END
                        and (first_tradeID == 1
                             or (currencyPair == 'BTC_HUC'
                                 and first_tradeID == 2)
                             or (currencyPair == 'BTC_RIC'
                                 and first_tradeID == 2)
                             or (currencyPair == 'BTC_XCP'
                                 and first_tradeID == 2)
                             or (currencyPair == 'BTC_NAV'
                                 and first_tradeID == 4569)
                             or (currencyPair == 'BTC_POT'
                                 and first_tradeID == 23511))):
                        return

        except Exception as e:
            log.error('Error opening file: {}'.format(csv_fn))
            log.exception(e)

        '''
        Poloniex API limits querying TradeHistory to intervals smaller
        than 1 month, so we make sure that start date is never more than
        1 month apart from end date
        '''
        if(end - start > 2419200):   # 60s/min * 60min/hr * 24hr/day * 28days
            newstart = end - 2419200
        else:
            newstart = start

        log.debug('{}: Retrieving from {} to {}\t {} - {}'.format(
                    currencyPair, str(newstart), str(end),
                    time.ctime(newstart), time.ctime(end)))

        url = '{path}command=returnTradeHistory&currencyPair={pair}' \
              '&start={start}&end={end}'.format(
                    path=self._api_path,
                    pair=currencyPair,
                    start=str(newstart),
                    end=str(end)
                )

        attempts = 0
        success = 0
        while attempts < CONN_RETRIES:
            try:
                response = requests.get(url)
            except Exception as e:
                log.error('Failed to retrieve trade history data'
                          'for {}'.format(currencyPair))
                log.exception(e)
                attempts += 1
            else:
                try:
                    if(isinstance(response.json(), dict)
                       and response.json()['error']):
                        log.error('Failed to to retrieve trade history data '
                                  'for {}: {}'.format(
                                    currencyPair,
                                    response.json()['error']
                                    ))
                        attempts += 1
                except Exception as e:
                    log.exception(e)
                    attempts += 1
                else:
                    success = 1
                    break

        if not success:
            return None

        '''
        If we get to transactionId == 1, and we already have that on
        disk, we got to the end of TradeHistory for this coin.
        '''
        if('first_tradeID' in locals()
                and response.json()[-1]['tradeID'] == first_tradeID):
            return

        '''
            There are primarily two scenarios:
                a) There is newer data available that we need to add at
                   the beginning of the file. We'll retrieve all what we
                   need until we get to what we already have, writing it
                   to a temporary file; and we will write that at the
                   beginning of our existing file.
                b) We are going back in time, appending at the end of
                   our existing TradeHistory until the first transaction
                   for this currencyPair
        '''
        try:
            if(temp is not None
                    or ('end_file' in locals() and end_file + 3600 < end)):
                if (temp is None):
                    temp = os.tmpfile()
                tempcsv = csv.writer(temp)
                for item in response.json():
                    if(item['tradeID'] <= last_tradeID):
                        continue
                    tempcsv.writerow([
                        item['tradeID'],
                        item['date'],
                        item['type'],
                        item['rate'],
                        item['amount'],
                        item['total'],
                        item['globalTradeID'],
                    ])
                if(response.json()[-1]['tradeID'] > last_tradeID):
                    end = pd.to_datetime(response.json()[-1]['date'],
                                         infer_datetime_format=True
                                         ).value // 10**9
                    self.retrieve_trade_history(currencyPair, start,
                                                end, temp=temp)
                else:
                    with open(csv_fn, 'rb+') as f:
                        shutil.copyfileobj(f, temp)
                        f.seek(0)
                        temp.seek(0)
                        shutil.copyfileobj(temp, f)
                    temp.close()
                    end = start_file
            else:
                with open(csv_fn, 'ab') as csvfile:
                    csvwriter = csv.writer(csvfile)
                    for item in response.json():
                        if('first_tradeID' in locals()
                                and item['tradeID'] >= first_tradeID):
                            continue
                        csvwriter.writerow([
                            item['tradeID'],
                            item['date'],
                            item['type'],
                            item['rate'],
                            item['amount'],
                            item['total'],
                            item['globalTradeID']
                        ])
                end = pd.to_datetime(response.json()[-1]['date'],
                                     infer_datetime_format=True).value//10**9

        except Exception as e:
            log.error('Error opening {}'.format(csv_fn))
            log.exception(e)

        '''
            If we got here, we aren't done yet. Call recursively with
            'end' times that go sequentially back in time.
        '''
        self.retrieve_trade_history(currencyPair, start, end)

    def generate_ohlcv(self, df):
        '''
        Generates OHLCV dataframe from a dataframe containing all TradeHistory
        by resampling with 1-minute period
        '''
        df.set_index('date', inplace=True)             # Index by date
        vol = df['total'].to_frame('volume')           # set Vol aside
        df.drop('total', axis=1, inplace=True)         # Drop volume data
        ohlc = df.resample('T').ohlc()                 # Resample OHLC 1min
        ohlc.columns = ohlc.columns.map(lambda t: t[1])  # Rename cols
        closes = ohlc['close'].fillna(method='pad')    # Pad fwd missing close
        ohlc = ohlc.apply(lambda x: x.fillna(closes))  # Fill NA w/ last close
        vol = vol.resample('T').sum().fillna(0)        # Add volumes by bin
        ohlcv = pd.concat([ohlc, vol], axis=1)         # Concat OHLC + Vol
        return ohlcv

    def write_ohlcv_file(self, currencyPair):
        '''
        Generates OHLCV data file with 1minute bars from TradeHistory on disk
        '''
        csv_trades = CSV_OUT_FOLDER + 'crypto_trades-' + currencyPair + '.csv'
        csv_1min = CSV_OUT_FOLDER + 'crypto_1min-' + currencyPair + '.csv'
        if(os.path.getmtime(csv_1min) > time.time() - 7200):
            log.debug(currencyPair+': 1min data file already up to date. '
                      'Delete the file if you want to rebuild it.')
        else:
            df = pd.read_csv(csv_trades,
                             names=['tradeID',
                                    'date',
                                    'type',
                                    'rate',
                                    'amount',
                                    'total',
                                    'globalTradeID'],
                             dtype={'tradeID': int,
                                    'date': str,
                                    'type': str,
                                    'rate': float,
                                    'amount': float,
                                    'total': float,
                                    'globalTradeID': int}
                             )
            df.drop(['tradeID', 'type', 'amount', 'globalTradeID'],
                    axis=1, inplace=True)
            df['date'] = pd.to_datetime(df['date'], infer_datetime_format=True)
            ohlcv = self.generate_ohlcv(df)
            try:
                with open(csv_1min, 'w') as csvfile:
                    csvwriter = csv.writer(csvfile)
                    for item in ohlcv.itertuples():
                        if item.Index == 0:
                            continue
                        csvwriter.writerow([
                            item.Index.value // 10 ** 9,
                            item.open,
                            item.high,
                            item.low,
                            item.close,
                            item.volume,
                        ])
            except Exception as e:
                log.error('Error opening {}'.format(csv_1min))
                log.exception(e)
            log.debug('{}: Generated 1min OHLCV data.'.format(currencyPair))

    def onemin_to_dataframe(self, currencyPair, start, end):
        '''
        Returns a data frame for a given currencyPair from data on disk
        '''
        csv_fn = CSV_OUT_FOLDER + 'crypto_1min-' + currencyPair + '.csv'
        df = pd.read_csv(csv_fn, names=['date',
                                        'open',
                                        'high',
                                        'low',
                                        'close',
                                        'volume'])
        df['date'] = pd.to_datetime(df['date'], unit='s')
        df.set_index('date', inplace=True)
        return df[start:end]

    def generate_symbols_json(self, filename=None):
        '''
        Generates a symbols.json file with corresponding start_date
        for each currencyPair
        '''
        symbol_map = {}

        if(filename is None):
            filename = get_exchange_symbols_filename('poloniex')

        with open(filename, 'w') as symbols:
            for currencyPair in self.currency_pairs:
                start = None
                csv_fn = '{}crypto_trades-{}.csv'.format(
                                                    CSV_OUT_FOLDER,
                                                    currencyPair)
                with open(csv_fn, 'r') as f:
                    f.seek(0, os.SEEK_END)
                    if(f.tell() > 2):               # Check file size is not 0
                        f.seek(-2, os.SEEK_END)     # Jump to 2nd last byte
                        while f.read(1) != b"\n":   # Until EOL is found...
                            # ...jump back the read byte plus one more.
                            f.seek(-2, os.SEEK_CUR)
                        start = pd.to_datetime(f.readline().split(',')[1],
                                               infer_datetime_format=True)

                if(start is None):
                    start = time.gmtime()
                quote, base = currencyPair.lower().split('_')
                symbol = '{base}_{quote}'.format(base=base, quote=quote)
                symbol_map[currencyPair] = dict(
                    symbol=symbol,
                    start_date=start.strftime("%Y-%m-%d")
                )
            json.dump(symbol_map, symbols, sort_keys=True, indent=2,
                      separators=(',', ':'))


if __name__ == '__main__':
    pc = PoloniexCurator()
    pc.get_currency_pairs()
    # pc.generate_symbols_json()

    for currencyPair in pc.currency_pairs:
        pc.retrieve_trade_history(currencyPair)
        log.debug('{} up to date.'.format(currencyPair))
        pc.write_ohlcv_file(currencyPair)
