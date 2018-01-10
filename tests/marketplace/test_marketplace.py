from catalyst.marketplace.marketplace import Marketplace
from catalyst.testing.fixtures import WithLogger, ZiplineTestCase


class TestMarketplace(WithLogger, ZiplineTestCase):
    def test_list(self):
        marketplace = Marketplace()
        marketplace.list()
        pass

    def test_register(self):
        marketplace = Marketplace()
        marketplace.register('GitHub')
        pass
