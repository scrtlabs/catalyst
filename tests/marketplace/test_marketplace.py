from catalyst.marketplace.marketplace import Marketplace
from catalyst.testing.fixtures import WithLogger, ZiplineTestCase
import pandas as pd


class TestMarketplace(WithLogger, ZiplineTestCase):
    def test_list(self):
        marketplace = Marketplace()
        marketplace.list()
        pass

    def test_register(self):
        marketplace = Marketplace()
        marketplace.register()
        pass

    def test_subscribe(self):
        marketplace = Marketplace()
        marketplace.subscribe('marketcap2222')
        pass

    def test_ingest(self):
        marketplace = Marketplace()
        ds_def = marketplace.ingest('marketcap1234')
        pass

    def test_publish(self):
        marketplace = Marketplace()
        datadir = '/Users/fredfortier/Downloads/marketcap_test_single'
        marketplace.publish('marketcap1234', datadir, False)
        pass

    def test_clean(self):
        marketplace = Marketplace()
        marketplace.clean('marketcap')
        pass
