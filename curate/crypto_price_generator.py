import urllib, json, time, csv
from datetime import datetime
import pandas as pd
import os
import time

# Pulled from https://github.com/absortium/poloniex-api/blob/master/poloniex/constants.py
CURRENCY_PAIRS = [
    "BTC_AMP",
    "BTC_ARDR",
    "BTC_BCN",
    "BTC_BCY",
    "BTC_BELA",
    "BTC_BLK",
    "BTC_BTCD",
    "BTC_BTM",
    "BTC_BTS",
    "BTC_BURST",
    "BTC_CLAM",
    "BTC_DASH",
    "BTC_DCR",
    "BTC_DGB",
    "BTC_DOGE",
    "BTC_EMC2",
    "BTC_ETC",
    "BTC_ETH",
    "BTC_EXP",
    "BTC_FCT",
    "BTC_FLDC",
    "BTC_FLO",
    "BTC_GAME",
    "BTC_GNO",
    "BTC_GNT",
    "BTC_GRC",
    "BTC_HUC",
    "BTC_LBC",
    "BTC_LSK",
    "BTC_LTC",
    "BTC_MAID",
    "BTC_NAUT",
    "BTC_NAV",
    "BTC_NEOS",
    "BTC_NMC",
    "BTC_NOTE",
    "BTC_NXC",
    "BTC_NXT",
    "BTC_OMNI",
    "BTC_PASC",
    "BTC_PINK",
    "BTC_POT",
    "BTC_PPC",
    "BTC_RADS",
    "BTC_REP",
    "BTC_RIC",
    "BTC_SBD",
    "BTC_SC",
    "BTC_SJCX",
    "BTC_STEEM",
    "BTC_STR",
    "BTC_STRAT",
    "BTC_SYS",
    "BTC_VIA",
    "BTC_VRC",
    "BTC_VTC",
    "BTC_XBC",
    "BTC_XCP",
    "BTC_XEM",
    "BTC_XMR",
    "BTC_XPM",
    "BTC_XRP",
    "BTC_XVC",
    "BTC_ZEC",
    "ETH_ETC",
    "ETH_GNO",
    "ETH_GNT",
    "ETH_LSK",
    "ETH_REP",
    "ETH_STEEM",
    "ETH_ZEC",
    "USDT_BTC",
    "USDT_DASH",
    "USDT_ETC",
    "USDT_ETH",
    "USDT_LTC",
    "USDT_NXT",
    "USDT_REP",
    "USDT_STR",
    "USDT_XMR",
    "USDT_XRP",
    "USDT_ZEC",
    "XMR_BCN",
    "XMR_BLK",
    "XMR_BTCD",
    "XMR_DASH",
    "XMR_LTC",
    "XMR_MAID",
    "XMR_NXT",
    "XMR_ZEC"
]


# CURRENCY_PAIRS = [
#     "BTC_AMP",
#     "BTC_ARDR"
# ]

DT_START = time.mktime(datetime(2010, 01, 01, 0, 0).timetuple())
# DT_START = time.mktime(datetime(2017, 06, 13, 0, 0).timetuple()) # TODO: remove temp
CSV_OUT = 'data/crypto_prices.csv'

class PoloniexDataGenerator(object):
    """
    OHLCV data feed generator for crypto data. Based on Poloniex market data
    """

    def __init__(self):
    	self._api_path = 'https://poloniex.com/public?command=returnChartData'
    	# &currencyPair=BTC_ETH&start=1435699200&end=9999999999&period=300'

    # TODO: return latest appended date
    def _get_start_date(self, csv_fn):
    	try:
    		with open(csv_fn, 'rb') as csvfile:
    			# read last line
        		lastrow = None
        		for lastrow in csv.reader(csvfile): pass
        		# print 'lastrow is %s' % lastrow
        		return long(lastrow[0]) + 300
        except:
        	pass

        return DT_START


    def get_data(self, currencyPair, start, end=9999999999, period=300):
    	url = self._api_path + '&currencyPair=' + currencyPair + '&start=' + str(start) + '&end=' + str(end) + '&period=' + str(period)
    	response = urllib.urlopen(url)
    	data = json.loads(response.read())
    	return data


    '''
    Pulls latest data for a single pair
    '''
    def append_data_single_pair(self, currencyPair):
    	print 'Getting data for %s' % currencyPair

    	def run_append(currencyPair):
	    	csv_fn = CSV_OUT + '-' + currencyPair + '.csv'
	    	start = self._get_start_date(csv_fn)
	    	data = self.get_data(currencyPair, start)
	    	with open(csv_fn, 'ab') as csvfile:
	    		csvwriter = csv.writer(csvfile)
	    		for item in data:
	    			if item['date'] == 0:
	    				continue
	    			csvwriter.writerow([item['date'], item['open'], item['high'], item['low'], item['close'], item['volume']])

    	try:
    		run_append(currencyPair)
    	except:
    		print 'Failed getting %s. Retrying ...' % currencyPair
    		try:
    			run_append(currencyPair)
    		except:
    			print 'Faile twice getting %s. Giving up ...' % currencyPair

    '''
    Pulls latest data for all currency pairs
    '''
    def append_data(self):
    	for currencyPair in CURRENCY_PAIRS:
    		self.append_data_single_pair(currencyPair)
    		time.sleep(10)


    '''
    Returns a data frame for all pairs, or for the requests currency pair.
    Makes sure data is up to date
    '''
    def to_dataframe(self, start, end, currencyPair=None):
    	csv_fn = CSV_OUT + '-' + currencyPair + '.csv'
    	last_date = self._get_start_date(csv_fn)
    	if last_date + 300 < end or not os.path.exists(csv_fn):
    		# get latest data
    		self.append_data_single_pair(currencyPair)

    	# CSV holds the latest snapshot
    	df = pd.read_csv(csv_fn,  names=['date', 'open', 'high', 'low', 'close', 'volume'])
    	df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    	return df.loc[(df['date'] > start) & (df['date'] <= end)]


# from zipline.utils.calendars import get_calendar
# from zipline.data.us_equity_pricing import (
#     BcolzDailyBarWriter,
#     BcolzDailyBarReader,
# )

# open_calendar = get_calendar('OPEN')

# start_session = pd.Timestamp('2012-12-31', tz='UTC')
# end_session = pd.Timestamp('2015-01-01', tz='UTC')

# file_path = 'test.bcolz'

# writer = BcolzDailyBarWriter(
#     file_path,
#     open_calendar,
#     start_session,
#     end_session
# )

# index = open_calendar.schedule.index
# index = index[
#     (index.date >= start_session.date()) &
#     (index.date <= end_session.date())
# ]

# data = pd.DataFrame(
#     0,
#     index=index,
#     columns=['open', 'high', 'low', 'close', 'volume'],
# )

# writer.write(
#     [(0, data)],
#     assets=[0],
#     show_progress=True
# )

# print 'len(index):', len(index)

# reader = BcolzDailyBarReader(file_path)

# print 'first_rows:', reader._first_rows
# print 'last_rows:',  reader._last_rows
