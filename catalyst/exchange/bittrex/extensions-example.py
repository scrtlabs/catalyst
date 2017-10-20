from catalyst.data.bundles import register
from catalyst.exchange.exchange_bundle import exchange_bundle

symbols = (
    'neo_btc',
)
register('exchange_bitfinex', exchange_bundle('bitfinex', symbols))