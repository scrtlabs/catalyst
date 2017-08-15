# code
from catalyst.api import order, record, symbol
from catalyst.exchange.algorithm_exchange import ExchangeTradingAlgorithm
from datetime import timedelta
from catalyst.exchange.bitfinex import Bitfinex
import pandas as pd

bitfinex = Bitfinex()


def initialize(context):
    pass


def handle_data(context, data):
    asset = bitfinex.get_asset('eth_usd')
    test = data.current(asset, 'close')
    order(symbol('AAPL'), 10)


algo_obj = ExchangeTradingAlgorithm(
    initialize=initialize,
    handle_data=handle_data,
    start=pd.Timestamp.utcnow(),
    end=pd.Timestamp.utcnow() + timedelta(hours=1),
    exchange=bitfinex,
)
perf_manual = algo_obj.run()
