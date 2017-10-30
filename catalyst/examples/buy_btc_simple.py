'''
	This is a very simple example referenced in the beginner's tutorial:
	https://enigmampc.github.io/catalyst/beginner-tutorial.html

	Run this example, by executing the following from your terminal:
	catalyst run -f buy_btc_simple.py -x bitfinex --start 2016-1-1 --end 2017-9-30 -o buy_btc_simple_out.pickle

	If you want to run this code using another exchange, make sure that 
	the asset is available on that exchange. For example, if you were to run 
	it for exchange Poloniex, you would need to edit the following line:

		context.asset = symbol('btc_usdt')     # note 'usdt' instead of 'usd'

	and specify exchange poloniex as follows:

	catalyst run -f buy_btc_simple.py -x poloniex --start 2016-1-1 --end 2017-9-30 -o buy_btc_simple_out.pickle

	To see which assets are available on each exchange, visit:
	https://www.enigma.co/catalyst/status
'''

from catalyst.api import order, record, symbol

def initialize(context):
    context.asset = symbol('btc_usd')

def handle_data(context, data):
    order(context.asset, 1)
    record(btc = data.current(context.asset, 'price'))