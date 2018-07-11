from catalyst.marketplace.marketplace import Marketplace
from catalyst.testing.fixtures import WithLogger, CatalystTestCase


class TestMarketplace(WithLogger, CatalystTestCase):
    def _test_list(self):
        marketplace = Marketplace()
        marketplace.list()
        pass

    def _test_register(self):
        marketplace = Marketplace()
        marketplace.register()
        pass

    def _test_subscribe(self):
        marketplace = Marketplace()
        marketplace.subscribe('marketcap')
        pass

    def _test_ingest(self):
        marketplace = Marketplace()
        ds_def = marketplace.ingest('marketcap')
        print(ds_def)
        pass

    def _test_publish(self):
        marketplace = Marketplace()
        datadir = '/Users/fredfortier/Downloads/marketcap_test_single'
        marketplace.publish('marketcap1234', datadir, False)
        pass

    def _test_clean(self):
        marketplace = Marketplace()
        marketplace.clean('marketcap')
        pass
