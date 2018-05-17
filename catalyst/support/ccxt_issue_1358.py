import ccxt

bitfinex = ccxt.bitfinex()
bitfinex.verbose = True
ohlcvs = bitfinex.fetch_ohlcv('ETH/BTC', '30m', 1504224000000)

dt = bitfinex.iso8601(ohlcvs[0][0])
print(dt)  # should print '2017-09-01T00:00:00.000Z'
