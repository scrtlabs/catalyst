'''
    This is a very simple example referenced in the beginner's tutorial:
    https://enigmampc.github.io/catalyst/beginner-tutorial.html

    Run this example, by executing the following from your terminal:
      catalyst ingest-exchange -x bitfinex -f daily -i btc_usdt
      catalyst run -f buy_btc_simple.py -x bitfinex --start 2016-1-1 \
        --end 2017-9-30 -o buy_btc_simple_out.pickle

    If you want to run this code using another exchange, make sure that
    the asset is available on that exchange. For example, if you were to run
    it for exchange Poloniex, you would need to edit the following line:

        context.asset = symbol('btc_usdt')     # note 'usdt' instead of 'usd'

    and specify exchange poloniex as follows:
    catalyst ingest-exchange -x poloniex -f daily -i btc_usdt
    catalyst run -f buy_btc_simple.py -x poloniex --start 2016-1-1 \
        --end 2017-9-30 -o buy_btc_simple_out.pickle

    To see which assets are available on each exchange, visit:
    https://www.enigma.co/catalyst/status
'''
from catalyst import run_algorithm
from catalyst.api import order_target, record, symbol, order, order_target_percent, set_commission
import pandas as pd


def initialize(context):
    context.asset = symbol('btc_usdt')
    # context.asset = symbol('etc_btc')
    context.i = 0
    # context.set_commission(maker=0.4,taker=0.3)

# def handle_data(context, data):
#     context.i += 1
#     if context.i == 1:
#         order_target(context.asset, 3, limit_price=0.00231)
#     if context.i == 2:
#         order(context.asset, -1, limit_price=0.0023145)
#         order(context.asset, -1, limit_price=0.0023146)
#         order(context.asset, 3, limit_price=0.0023146)
#     record(btc=data.current(context.asset, 'price'))


def handle_data(context, data):
    if not context.blotter.open_orders:
        if context.portfolio.positions and context.portfolio.positions[context.asset].amount > 0.5:
            order_target(context.asset, 0, limit_price=(data.current(context.asset, 'price')+0.00013))
        else:
            order_target(context.asset, 1, limit_price=(data.current(context.asset, 'price')+0.00003))

    record(btc=data.current(context.asset, 'price'))

# def handle_data(context, data):
#     context.i += 1
#     if context.i % 2 == 1:# if not context.blotter.open_orders:
#         order_target(context.asset, 1, limit_price=data.current(context.asset, 'price'))

    # record(btc=data.current(context.asset, 'price'))


if __name__ == '__main__':
    live = True
    if live:
        run_algorithm(
            capital_base=0.02,
            data_frequency='daily',
            initialize=initialize,
            handle_data=handle_data,
            exchange_name='poloniex',
            algo_namespace='buy_btc_simple',
            quote_currency='btc',
            live=True,
            # simulate_orders=False,
            # start=pd.to_datetime('2018-05-01 17:18', utc=True),
            end=pd.to_datetime('2018-05-14 08:28', utc=True),
        )
    else:
        run_algorithm(
                capital_base=100000,
                data_frequency='daily',
                initialize=initialize,
                handle_data=handle_data,
                exchange_name='poloniex',
                algo_namespace='buy_btc_simple',
                quote_currency='usdt',
                start=pd.to_datetime('2016-01-01', utc=True),
                end=pd.to_datetime('2016-01-03', utc=True),
            )
