import json, time, csv
from datetime import datetime
import pandas as pd
import os
import time
import requests
import logbook

DT_START        = time.mktime(datetime(2010, 1, 1, 0, 0).timetuple())
CSV_OUT_FOLDER  = '/var/tmp/catalyst/data/poloniex/'
CONN_RETRIES    = 2

logbook.StderrHandler().push_application()
log = logbook.Logger(__name__)

class PoloniexCurator(object):
    """
    OHLCV data feed generator for crypto data. Based on Poloniex market data
    """

    _api_path       = 'https://poloniex.com/public?'
    currency_pairs  = []

    def __init__(self):
        if not os.path.exists(CSV_OUT_FOLDER):
            try:
                os.makedirs(CSV_OUT_FOLDER)
            except Exception as e:
                log.error('Failed to create data folder: %s' % CSV_OUT_FOLDER)
                log.exception(e)

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

    def _get_start_date(self, csv_fn):
        ''' Function returns latest appended date, if the file has been previously written
            the last line is an empty one, so we have to read the second to last line 
        '''
        try:
            with open(csv_fn, 'ab+') as f: 
                f.seek(0, os.SEEK_END)              # First check file is not zero size
                if(f.tell() > 2):
                    f.seek(-2, os.SEEK_END)         # Jump to the second last byte.
                    while f.read(1) != b"\n":       # Until EOL is found...
                        f.seek(-2, os.SEEK_CUR)     # ...jump back the read byte plus one more.
                    lastrow = f.readline() 
                    return int(lastrow.split(',')[0]) + 300

        except Exception as e:
            log.error('Error opening file: %s' % csv_fn)
            log.exception(e)

        return DT_START

    def get_data(self, currencyPair, start, end=9999999999, prev_df=None):
        log.debug(currencyPair+': Retrieving from '+str(start)+' to '+str(end))

        '''
        Poloniex limits a single query to returnTradeHistory to less than a year between start and end
        '''
        if(end == 9999999999 and time.time() - start > 365*86400 ):     
            newstart = time.time() - 360*86400
        elif( end != 9999999999 and end - start > 365*86400 ):
            newstart = end - 360*86400
        else:
            newstart = start
        
        url = self._api_path + 'command=returnTradeHistory&currencyPair=' + currencyPair + '&start=' + str(newstart) + '&end=' + str(end)

        try:
            response = requests.get(url)
        except Exception as e:
            log.error('Failed to retrieve trade history data for %s' % currencyPair)
            log.exception(e)
            return None

        log.debug(currencyPair+': Received '+str(len(response.json()))+' trades.')
        if(len(response.json())==1 and not isinstance(response.json(),list)):
            r = response.json()
            print(r)
            if(r['error']):
                log.error(r['error'])
                return None

        df = pd.DataFrame(data=response.json(), columns = ['date','rate', 'total', 'tradeID']) 
        df['rate']    = pd.to_numeric( df['rate'],    errors='coerce')                # Convert rate to float
        df['total']   = pd.to_numeric( df['total'],   errors='coerce')                # Convert vol to float
        df['tradeID'] = pd.to_numeric( df['tradeID'], errors='coerce')                # Convert vol to float                       
        df['date']    = pd.to_datetime(df['date'],    infer_datetime_format=True)     # Convert date
        df.set_index('tradeID', inplace=True)                                         # Index by tradeID
        df = df.iloc[::-1]                         # Reverse timeseries as TradeHistory is provided newest to oldest

        if(prev_df is not None):
            if(prev_df.index[0] == df.index[0]):
                return prev_df
            df = prev_df.combine_first(df)

        first = df['date'].iloc[0].value // 10 ** 9
        df = self.get_data( currencyPair, start, first, df )
        return df


    def generate_ohlcv(self, df):

        df.set_index('date', inplace=True)                      # Index by date
        vol = df['total'].to_frame('volume')                    # Will deal with vol separately, as ohlc() messes it up
        df.drop('total', axis=1, inplace=True)                  # Drop volume data from dataframe
        ohlc = df.resample('T').ohlc()                          # Resample OHLC in 5min bins
        ohlc.columns = ohlc.columns.map(lambda t: t[1])         # Raname columns by dropping 'rate'
        closes = ohlc['close'].fillna(method='pad')             # Pad forward missing 'close'
        ohlc = ohlc.apply(lambda x: x.fillna(closes))           # Fill N/A with last close
        vol = vol.resample('T').sum().fillna(0)                 # Add volumes by bin
        ohlcv = pd.concat([ohlc,vol], axis=1)                   # Concatenate OHLC + Volume

        return ohlcv
    
    '''
    Pulls latest data for a single pair
    '''
    def append_data_single_pair(self, currencyPair, repeat=0):
        log.debug('Getting data for %s' % currencyPair)
        csv_fn = CSV_OUT_FOLDER + 'crypto_prices-' + currencyPair + '.csv'
        start  = self._get_start_date(csv_fn)
        # Only fetch data if more than 5min have passed since last fetch
        if (time.time() > start):
            data = self.get_data(currencyPair, start)

            if data is not None:
                ohlcv = self.generate_ohlcv(data)

                try: 
                    with open(csv_fn, 'ab') as csvfile:
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
            elif (repeat < CONN_RETRIES):
                    log.debug('Retrying: attemt %d' % (repeat+1) )
                    self.append_data_single_pair(currencyPair, repeat + 1)    

    '''
    Pulls latest data for all currency pairs
    '''
    def append_data(self):
        for currencyPair in self.currency_pairs:
            self.append_data_single_pair(currencyPair)
            # Rate limit is 6 calls per second, sleep 1sec/6 to be safe
            time.sleep(0.17)

    '''
    Returns a data frame for all pairs, or for the requests currency pair.
    Makes sure data is up to date
    '''
    def to_dataframe(self, start, end, currencyPair=None):
        csv_fn = CSV_OUT_FOLDER + 'crypto_prices-' + currencyPair + '.csv'
        last_date = self._get_start_date(csv_fn)
        if last_date + 300 < end or not os.path.exists(csv_fn):
            # get latest data
            self.append_data_single_pair(currencyPair)

        # CSV holds the latest snapshot
        df = pd.read_csv(csv_fn, names=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date']=pd.to_datetime(df['date'],unit='s')
        df.set_index('date', inplace=True)

        return df[datetime.fromtimestamp(start):datetime.fromtimestamp(end-1)]

if __name__ == '__main__':
    pc = PoloniexCurator()
    pc.get_currency_pairs()
    pc.append_data()
