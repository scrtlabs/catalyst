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
        marketplace.register('GitHub')
        pass

    def test_ingest(self):
        marketplace = Marketplace()
        marketplace.ingest(
            data_source_name='Marketcap',
            data_frequency='finest',
            start=pd.Timestamp.utcnow(),
            force_download=True,
        )
        pass
