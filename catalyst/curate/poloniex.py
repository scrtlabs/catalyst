import json, time, csv
from datetime import datetime
import pandas as pd
import os
import time
import requests
import logbook

DT_START        = time.mktime(datetime(2010, 01, 01, 0, 0).timetuple())
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

    def get_data(self, currencyPair, start, end=9999999999, period=300):
    	url = self._api_path + 'command=returnChartData&currencyPair=' + currencyPair + '&start=' + str(start) + '&end=' + str(end) + '&period=' + str(period)
        
        try:
            response = requests.get(url)
        except Exception as e:
            log.error('Failed to retrieve candlestick chart data for %s' % currencyPair)
            log.exception(e)
            return None

    	return response.json()

    '''
    Pulls latest data for a single pair
    '''
    def append_data_single_pair(self, currencyPair, repeat=0):
    	log.debug('Getting data for %s' % currencyPair)
        csv_fn = CSV_OUT_FOLDER + 'crypto_prices-' + currencyPair + '.csv'
        start  = self._get_start_date(csv_fn)
        # Only fetch data if more than 5min have passed since last fetch
        if (time.time() > start):
            data   = self.get_data(currencyPair, start)
            if data is not None:
                try: 
                    with open(csv_fn, 'ab') as csvfile:
                        csvwriter = csv.writer(csvfile)
                        for item in data:
                            if item['date'] == 0:
                                continue
                            csvwriter.writerow([
                                item['date'],
                                item['open'],
                                item['high'],
                                item['low'],
                                item['close'],
                                item['volume'],
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
