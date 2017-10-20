from catalyst.api import order, record, symbol

def initialize(context):
    context.asset = symbol('btc_usd')

def handle_data(context, data):
    order(context.asset, 1)
    record(btc = data.current(context.asset, 'price'))