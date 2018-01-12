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
        ds_def = marketplace.get_data_source_def('Marketcap')

        marketplace.ingest(
            data_source_name='Marketcap',
            data_frequency=ds_def['data_frequencies'][0],
            start=pd.to_datetime('2017-10-01'),
            force_download=True,
        )
        pass

    def test_clean(self):
        marketplace = Marketplace()
        marketplace.clean('marketcap')
        pass
