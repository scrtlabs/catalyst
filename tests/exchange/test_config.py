from catalyst.exchange.utils.factory import get_exchange


class TestConfig:
    def test_create_config(self):
        exchange = get_exchange('binance', skip_init=True)
        config = exchange.create_exchange_config()
        pass
