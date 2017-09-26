#!/usr/bin/env python
import json
import time
import hmac
import hashlib

from six.moves import urllib

# Workaround for backwards compatibility
# https://stackoverflow.com/questions/3745771/urllib-request-in-python-2-7
urlopen = urllib.request.urlopen


class Poloniex_api(object):
    def __init__(self, key, secret):
        self.key = key
        self.secret = secret
        self.public  = ['returnTicker', 'return24Volume', 'returnOrderBook',
                        'returnTradeHistory', 'returnChartData',
                        'returnCurrencies', 'returnLoanOrders']
        self.trading = ['returnBalances','returnCompleteBalances','returnDepositAddresses',
                        'generateNewAddress','returnDepositsWithdrawals','returnOpenOrders',
                        'returnTradeHistory','returnOrderTrades',
                        'buy', 'sell', 'cancelOrder', 'moveOrder',
                        'withdraw', 'returnFeeInfo','returnAvailableAccountBalances',
                        'returnTradableBalances', 'transferBalance',
                        'returnMarginAccountSummary','marginBuy','marginSell',
                        'getMarginPosition', 'closeMarginPosition','createLoanOffer',
                        'cancelLoanOffer','returnOpenLoanOffers','returnActiveLoans',
                        'returnLendingHistory','toggleAutoRenew']

    def query(self, method, req={}):

        if method in self.public:
            url = 'https://poloniex.com/public?command=' + method + '&' + urllib.parse.urlencode(req)
            headers = {}
            post_data = None
        elif method in self.trading:
            url = 'https://poloniex.com/tradingApi'
            req['command'] = method
            req['nonce']   = int(time.time()*1000)
            post_data      = urllib.parse.urlencode(req)
            print(post_data)
            signature      = hmac.new(self.secret, post_data, hashlib.sha512).hexdigest()
            headers        = { 'Sign': signature, 'Key': self.key}
        else:
            raise ValueError('Method "' + method + '" not found in neither the Public API or Trading API endpoints')

        req = urllib.request.Request(url, data=post_data, headers=headers)
        return json.loads(urlopen(req).read())

    def returnticker(self):
        return self.query('returnTicker')

    def return24volume(self):
        return self.query('return24Volume')

    def returnOrderBook(self, market='all'):
        return self.query('returnOrderBook', {'currencyPair': market})

    def returntradehistory(self, market, start=None, end=None):
        if(start is not None and end is not None):
            return self.query('returntradehistory', 
                              {'currencyPair': market, 'start': start, 'end': end })
        else:
            return self.query('returntradehistory', {'currencyPair': market })

    def returnchartdata(self, market, period, start, end):
        return self.query('returnChartData', {'currencyPair': market, 'period': period,
                          'start': start, 'end': end})

    def returncurrencies(self):
        return self.query('returnCurrencies')

    def returnloadorders(self, market):
        return self.query('returnLoanOrders', {'currency': market})

    def returnbalances(self):
        return self.query('returnBalances')

    def returnopenorders(self, market):
        return self.query('returnOpenOrders', {'currencyPair': market})

    def cancelorder(self, ordernumber):
        return self.query('cancelOrder', {'orderNumber': ordernumber})

    '''
    def buylimit(self, market, quantity, rate):
        return self.query('buylimit', {'market': market, 'quantity': quantity,
                                       'rate': rate})

    def buymarket(self, market, quantity):
        return self.query('buymarket',
                          {'market': market, 'quantity': quantity})

    def selllimit(self, market, quantity, rate):
        return self.query('selllimit', {'market': market, 'quantity': quantity,
                                        'rate': rate})

    def sellmarket(self, market, quantity):
        return self.query('sellmarket',
                          {'market': market, 'quantity': quantity})

    def getbalance(self, currency):
        return self.query('getbalance', {'currency': currency})

    def getdepositaddress(self, currency):
        return self.query('getdepositaddress', {'currency': currency})

    def withdraw(self, currency, quantity, address):
        return self.query('withdraw',
                          {'currency': currency, 'quantity': quantity,
                           'address': address})

    def getorder(self, uuid):
        return self.query('getorder', {'uuid': uuid})

    def getorderhistory(self, market, count):
        return self.query('getorderhistory',
                          {'market': market, 'count': count})

    def getwithdrawalhistory(self, currency, count):
        return self.query('getwithdrawalhistory',
                          {'currency': currency, 'count': count})

    def getdeposithistory(self, currency, count):
        return self.query('getdeposithistory',
                          {'currency': currency, 'count': count})
    '''
