import json, time, csv
from datetime import datetime
import pandas as pd
import os, time, shutil, requests, logbook
from catalyst.exchange.exchange_utils import get_exchange_symbols_filename


DT_START        = int(time.mktime(datetime(2010, 1, 1, 0, 0).timetuple()))
DT_END          = int(time.time())
CSV_OUT_FOLDER  = '/var/tmp/catalyst/data/poloniex/'
CSV_OUT_FOLDER  = '/Volumes/enigma/data/poloniex/'
CONN_RETRIES    = 2

logbook.StderrHandler().push_application()
log = logbook.Logger(__name__)

class PoloniexCurator(object):
    '''
    OHLCV data feed generator for crypto data. Based on Poloniex market data
    '''

    _api_path       = 'https://poloniex.com/public?'
    currency_pairs  = []

    def __init__(self):
        if not os.path.exists(CSV_OUT_FOLDER):
            try:
                os.makedirs(CSV_OUT_FOLDER)
            except Exception as e:
                log.error('Failed to create data folder: %s' % CSV_OUT_FOLDER)
                log.exception(e)

    '''
        Retrieves and returns all currency pairs from the exchange 
    '''
    def get_currency_pairs(self):
        url = self._api_path + 'command=returnTicker'

        try:
            response = requests.get(url)
        except Exception as e:
            log.error('Failed to retrieve list of currency pairs')
            log.exception(e)
            return None

        data = response.json()
        self.currency_pairs  = []
        for ticker in data:
            self.currency_pairs.append(ticker)
        self.currency_pairs.sort()

        log.debug('Currency pairs retrieved successfully: %d' % (len(self.currency_pairs)))


    '''
        Helper function that reads tradeID and date fields from CSV readline
    '''
    def _retrieve_tradeID_date(self, row):
        tId = int(row.split(',')[0])
        d   = pd.to_datetime( row.split(',')[1], infer_datetime_format=True).value // 10 ** 9
        return tId, d

    '''
        Retrieves TradeHistory from exchange for a given currencyPair between start and end dates.
        If no start date is provided, uses a system-wide one (beginning of time for cryptotrading)
        If no end date is provided, 'now' is used
        Stores results in CSV file on disk.
        This function is called recursively to work around the limitations imposed by the provider API.
    '''
    def retrieve_trade_history(self, currencyPair, start=DT_START, end=DT_END, temp=None):
        csv_fn = CSV_OUT_FOLDER + 'crypto_trades-' + currencyPair + '.csv'

        '''
            Check what data we already have on disk, reading first and last lines from file.
            Data is stored on file from NEWEST to OLDEST.
        '''
        try:
            with open(csv_fn, 'ab+') as f: 
                f.seek(0, os.SEEK_END)
                if(f.tell() > 2):                           # First check file is not zero size
                    f.seek(0)                               # Go to the beginning to read first line
                    last_tradeID, end_file    = self._retrieve_tradeID_date(f.readline())
                    f.seek(-2, os.SEEK_END)                 # Jump to the second last byte.
                    while f.read(1) != b"\n":               # Until EOL is found...
                        f.seek(-2, os.SEEK_CUR)             # ...jump back the read byte plus one more.
                    first_tradeID, start_file = self._retrieve_tradeID_date(f.readline())

                    if( first_tradeID == 1 and end_file + 3600 > DT_END ):
                        return

        except Exception as e:
            log.error('Error opening file: %s' % csv_fn)
            log.exception(e)

        '''
        Poloniex API limits querying TradeHistory to intervals smaller than 1 month,
        so we make sure that start date is never more than 1 month apart from end date
        '''
        if( end - start > 2419200 ):       # 60 s/min * 60 min/hr * 24 hr/day * 28 days     
            newstart = end - 2419200
        else:
            newstart = start

        log.debug(currencyPair+': Retrieving from '+str(newstart)+' to '+str(end) +'\t '
                    + time.ctime(newstart) + ' - '+ time.ctime(end))

        url = self._api_path + 'command=returnTradeHistory&currencyPair=' + currencyPair + '&start=' + str(newstart) + '&end=' + str(end)

        try:
            response = requests.get(url)
        except Exception as e:
            log.error('Failed to retrieve trade history data for %s' % currencyPair)
            log.exception(e)
            return None
        else:
            if isinstance(response.json(), dict) and response.json()['error']:
                log.error('Failed to to retrieve trade history data for %s: %s' % (currencyPair,response.json()['error']))
                exit(1)

        '''
            If we get to transactionId == 1, and we already have that on disk, 
            we got to the end of TradeHistory for this coin.
        '''
        if('first_tradeID' in locals() and response.json()[-1]['tradeID'] == first_tradeID): 
            return

        '''
            There are primarily two scenarios:
                a) There is newer data available that we need to add at the beginning
                   of the file. We'll retrieve all what we need until we get to what 
                   we already have, writing it to a temporary file; and we will write
                   that at the beginning of our existing file.
                b) We are going back in time, appending at the end of our existing
                   TradeHistory until the first transaction for this currencyPair
        '''
        try: 
            if( 'end_file' in locals() and end_file + 3600 < end):
                if (temp is None):
                    temp = os.tmpfile()
                tempcsv = csv.writer(temp)
                for item in response.json():
                    if( item['tradeID'] <= last_tradeID ):
                        continue
                    tempcsv.writerow([
                        item['tradeID'],
                        item['date'],
                        item['type'],
                        item['rate'],
                        item['amount'],
                        item['total'],
                        item['globalTradeID']        
                    ])
                if( response.json()[-1]['tradeID'] > last_tradeID ):
                    end = pd.to_datetime( response.json()[-1]['date'], infer_datetime_format=True).value // 10 ** 9
                    self.retrieve_trade_history(currencyPair, start, end, temp=temp) 
                else:
                    with open(csv_fn,'rb+') as f:
                        shutil.copyfileobj(f,temp)
                        f.seek(0)
                        temp.seek(0)
                        shutil.copyfileobj(temp,f)
                    temp.close()
                    end = start_file
            else:
                with open(csv_fn, 'ab') as csvfile:
                    csvwriter = csv.writer(csvfile)
                    for item in response.json():
                        if( 'first_tradeID' in locals() and item['tradeID'] >= first_tradeID ):
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
                end = pd.to_datetime( response.json()[-1]['date'], infer_datetime_format=True).value // 10 ** 9

        except Exception as e:
            log.error('Error opening %s' % csv_fn)
            log.exception(e)

        '''
            If we got here, we aren't done yet. Call recursively with 'end' times
            that go sequentially back in time.
        '''
        self.retrieve_trade_history(currencyPair, start, end)


    '''
        Generates OHLCV dataframe from a dataframe containing all TradeHistory
        by resampling with 1-minute period
    '''
    def generate_ohlcv(self, df):
        df.set_index('date', inplace=True)                      # Index by date
        vol = df['total'].to_frame('volume')                    # Will deal with vol separately, as ohlc() messes it up
        df.drop('total', axis=1, inplace=True)                  # Drop volume data from dataframe
        ohlc = df.resample('T').ohlc()                          # Resample OHLC in 1min bins
        ohlc.columns = ohlc.columns.map(lambda t: t[1])         # Raname columns by dropping 'rate'
        closes = ohlc['close'].fillna(method='pad')             # Pad forward missing 'close'
        ohlc = ohlc.apply(lambda x: x.fillna(closes))           # Fill N/A with last close
        vol = vol.resample('T').sum().fillna(0)                 # Add volumes by bin
        ohlcv = pd.concat([ohlc,vol], axis=1)                   # Concatenate OHLC + Volume
        return ohlcv


    '''
        Generates OHLCV data file with 1minute bars from TradeHistory on disk
    '''
    def write_ohlcv_file(self, currencyPair):        
        csv_trades = CSV_OUT_FOLDER + 'crypto_trades-' + currencyPair + '.csv'
        csv_1min   = CSV_OUT_FOLDER + 'crypto_1min-' + currencyPair + '.csv'
        if( os.path.isfile(csv_1min) ):
            log.debug(currencyPair+': 1min data already present. Delete the file if you want to rebuild it.')
        else:
            df = pd.read_csv(csv_trades, names=['tradeID','date','type','rate','amount','total','globalTradeID'], 
                    dtype = {'tradeID': int, 'date': str, 'type': str, 'rate': float, 'amount': float, 'total': float, 'globalTradeID': int } )
            df.drop(['tradeID','type','amount','globalTradeID'], axis=1, inplace=True)
            df['date'] = pd.to_datetime(df['date'], infer_datetime_format=True) 
            ohlcv = self.generate_ohlcv(df)
            try: 
                with open(csv_1min, 'ab') as csvfile:
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
                log.error('Error opening %s' % csv_fn)
                log.exception(e)
            log.debug(currencyPair+': Generated 1min OHLCV data.')


    '''
    Returns a data frame for a given currencyPair from data on disk
    '''
    def onemin_to_dataframe(self, currencyPair, start, end):
        csv_fn     = CSV_OUT_FOLDER + 'crypto_1min-' + currencyPair + '.csv'
        df         = pd.read_csv(csv_fn, names=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'],unit='s')
        df.set_index('date', inplace=True)
        return df[start : end]

    '''
    Generates a symbols.json file with corresponding start_date for each currencyPair
    '''
    def generate_symbols_json(self, filename=None):
        symbol_map = {}

        if(filename is None):
            filename = get_exchange_symbols_filename('poloniex')

        with open(filename, 'w') as symbols:
            for currencyPair in self.currency_pairs:
                start = None
                csv_fn     = CSV_OUT_FOLDER + 'crypto_trades-' + currencyPair + '.csv'
                with open(csv_fn, 'r') as f: 
                    f.seek(0, os.SEEK_END)
                    if(f.tell() > 2):                           # First check file is not zero size
                        f.seek(-2, os.SEEK_END)                 # Jump to the second last byte.
                        while f.read(1) != b"\n":               # Until EOL is found...
                            f.seek(-2, os.SEEK_CUR)             # ...jump back the read byte plus one more.
                        start = pd.to_datetime( f.readline().split(',')[1], infer_datetime_format=True)

                if(start is None):
                    start = time.gmtime()
                base, market = currencyPair.lower().split('_')
                symbol = '{market}_{base}'.format( market=market, base=base )
                symbol_map[currencyPair] = dict(
                    symbol = symbol,
                    start_date = start.strftime("%Y-%m-%d")
                )
            json.dump(symbol_map, symbols, sort_keys=True, indent=2, separators=(',',':'))    


if __name__ == '__main__':
    pc = PoloniexCurator()
    pc.get_currency_pairs()
    #pc.generate_symbols_json()
    
    for currencyPair in pc.currency_pairs:
        pc.retrieve_trade_history(currencyPair)
        pc.write_ohlcv_file(currencyPair)

    