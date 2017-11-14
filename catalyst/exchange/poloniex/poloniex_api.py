#!/usr/bin/env python
import json
import time
import hmac
import hashlib
import ssl

from six.moves import urllib

# Workaround for backwards compatibility
# https://stackoverflow.com/questions/3745771/urllib-request-in-python-2-7
urlopen = urllib.request.urlopen


class Poloniex_api(object):
    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

        self.max_requests_per_second = 6
        self.request_cpt = dict()

        self.public = ['returnTicker', 'return24Volume', 'returnOrderBook',
                       'returnTradeHistory', 'returnChartData',
                       'returnCurrencies', 'returnLoanOrders']
        self.trading = ['returnBalances', 'returnCompleteBalances',
                        'returnDepositAddresses',
                        'generateNewAddress', 'returnDepositsWithdrawals',
                        'returnOpenOrders',
                        'returnTradeHistory', 'returnOrderTrades',
                        'buy', 'sell', 'cancelOrder', 'moveOrder',
                        'withdraw', 'returnFeeInfo',
                        'returnAvailableAccountBalances',
                        'returnTradableBalances', 'transferBalance',
                        'returnMarginAccountSummary', 'marginBuy',
                        'marginSell',
                        'getMarginPosition', 'closeMarginPosition',
                        'createLoanOffer',
                        'cancelLoanOffer', 'returnOpenLoanOffers',
                        'returnActiveLoans',
                        'returnLendingHistory', 'toggleAutoRenew']

    def ask_request(self):
        """
        Asks permission to issue a request to the exchange.
        The primary purpose is to avoid hitting rate limits.

        The application will pause if the maximum requests per minute
        permitted by the exchange is exceeded.

        :return boolean:

        """
        now = time.time()
        if not self.request_cpt:
            self.request_cpt = dict()
            self.request_cpt[now] = 0
            return True

        cpt_date = list(self.request_cpt.keys())[0]
        cpt = self.request_cpt[cpt_date]

        if now > cpt_date + 1:
            self.request_cpt = dict()
            self.request_cpt[now] = 0
            return True

        if cpt >= self.max_requests_per_second:

            time.sleep(1)

            now = time.time()
            self.request_cpt = dict()
            self.request_cpt[now] = 0
            return True
        else:
            self.request_cpt[cpt_date] += 1

    def query(self, method, req={}):

        if method in self.public:
            url = 'https://poloniex.com/public?command=' + method + '&' + \
                  urllib.parse.urlencode(req)
            headers = {}
            post_data = None
        elif method in self.trading:
            url = 'https://poloniex.com/tradingApi'
            req['command'] = method
            req['nonce'] = int(time.time() * 1000)
            post_data = urllib.parse.urlencode(req)

            signature = hmac.new(self.secret.encode('utf-8'),
                                 post_data.encode('utf-8'),
                                 hashlib.sha512).hexdigest()
            headers = {'Sign': signature, 'Key': self.key}

            post_data = post_data.encode('utf-8')
        else:
            raise ValueError(
                'Method "' + method + '" not found in neither the Public API '
                                      'or Trading API endpoints'
            )

        self.ask_request()
        req = urllib.request.Request(
            url,
            data=post_data,
            headers=headers,
        )
        return json.loads(
            urlopen(req, context=ssl._create_unverified_context()).read())

    def returnticker(self):
        return self.query('returnTicker', {})

    def return24volume(self):
        return self.query('return24Volume', {})

    def returnOrderBook(self, market='all'):
        return self.query('returnOrderBook', {'currencyPair': market})

    def returntradehistory(self, market, start=None, end=None):
        if (start is not None and end is not None):
            return self.query('returntradehistory',
                              {'currencyPair': market, 'start': start,
                               'end': end})
        else:
            return self.query('returntradehistory', {'currencyPair': market})

    def returnchartdata(self, market, period, start, end=9999999999):
        return self.query('returnChartData',
                          {'currencyPair': market, 'period': period,
                           'start': start, 'end': end})

    def returncurrencies(self):
        return self.query('returnCurrencies', {})

    def returnloadorders(self, market):
        return self.query('returnLoanOrders', {'currency': market})

    def returnbalances(self):
        return self.query('returnBalances')

    def returncompletebalances(self, account):
        if (account):
            return self.query('returnCompleteBalances', {'account': account})
        else:
            return self.query('returnCompleteBalances')

    def returndepositaddresses(self):
        return self.query('returnDepositAddresses')

    def generatenewaddress(self, currency):
        return self.query('generateNewAddress', {'currency': currency})

    def returnDepositsWithdrawals(self, start, end):
        return self.query('returnDepositsWithdrawals',
                          {'start': start, 'end': end})

    def returnopenorders(self, market):
        return self.query('returnOpenOrders', {'currencyPair': market})

    def returntradehistory(self, market):
        # TODO: optional start and/or end and limit
        return self.query('returnTradeHistory', {'currencyPair': market})

    def returnordertrades(self, ordernumber):
        return self.query('returnOrderTrades', {'orderNumber': ordernumber})

    def buy(self, market, amount, rate, fillorkill=0, immediateorcancel=0,
            postonly=0):
        if (fillorkill):
            return self.query('buy', {'currencyPair': market, 'rate': rate,
                                      'amount': amount,
                                      'fillOrKill': fillorkill, })
        elif (immediateorcancel):
            return self.query('buy', {'currencyPair': market, 'rate': rate,
                                      'amount': amount,
                                      'immediateOrCancel': immediateorcancel, })
        elif (postonly):
            return self.query('buy', {'currencyPair': market, 'rate': rate,
                                      'amount': amount,
                                      'postOnly': postonly, })
        else:
            return self.query('buy', {'currencyPair': market, 'rate': rate,
                                      'amount': amount, })

    def sell(self, market, amount, rate, fillorkill=0, immediateorcancel=0,
             postonly=0):
        if (fillorkill):
            return self.query('sell', {'currencyPair': market, 'rate': rate,
                                       'amount': amount,
                                       'fillOrKill': fillorkill, })
        elif (immediateorcancel):
            return self.query('sell', {'currencyPair': market, 'rate': rate,
                                       'amount': amount,
                                       'immediateOrCancel': immediateorcancel, })
        elif (postonly):
            return self.query('sell', {'currencyPair': market, 'rate': rate,
                                       'amount': amount,
                                       'postOnly': postonly, })
        else:
            return self.query('sell', {'currencyPair': market, 'rate': rate,
                                       'amount': amount, })

    def cancelorder(self, ordernumber):
        return self.query('cancelOrder', {'orderNumber': ordernumber})

    def withdraw(self, currency, quantity, address):
        return self.query('withdraw',
                          {'currency': currency, 'amount': quantity,
                           'address': address})

    def returnfeeinfo(self):
        return self.query('returnFeeInfo')
