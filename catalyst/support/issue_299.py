from catalyst.exchange.utils.factory import get_exchange

for exchange_name in ["gdax", "binance"]:
    exchange = get_exchange(exchange_name)
    assets = exchange.get_assets()
    print(exchange.tickers(assets[0:2]))
    print(exchange.tickers([assets[0]]))
