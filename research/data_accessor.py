import numpy as np
import pandas as pd

from os.path import expanduser

from catalyst.data.minute_bars import BcolzMinuteBarReader
from catalyst.exchange.utils.exchange_utils import get_sid


class OHLCVDataAccessor:
    """
    Class to retrieve OHLCV minute data from catalyst.

    Attributes:
        exchange (str): Exchange for which the data will be requested.
        catalyst_root (str): Root directory where Catalyst data is stored (normally "<home directory>//.catalyst").
        path (str): Path to the data bundle.
        reader (catalyst.data.minute_bars.BcolzMinuteBarReader): BcolzMinuteBarReader object doing the heavy lifting to
            retrieve the data.

    Example:
        >> import pandas as pd
        >> from catalyst.research.data_accessor import OHLCVDataAccessor
        >>
        >> symbol = ['eth_btc', 'xrp_btc']
        >> fields = ['open', 'high', 'low', 'close', 'volume', 'volume_quote']
        >> start_dt = pd.Timestamp('2018-01-01')
        >> end_dt = pd.Timestamp('2018-02-01')
        >>
        >> accessor = OHLCVDataAccessor(exchange='binance')
        >> ohlcv_data = accessor.get_data(symbol, fields, start_dt, end_dt)
        >> print(ohlcv_data.volume_quote)
        >> print(ohlcv_data)
    """
    def __init__(self, exchange=None, catalyst_root=None):
        if exchange is None:
            raise ValueError('You should provide the exchange for which you')
        if catalyst_root is None:
            home = expanduser("~")
            self.catalyst_root = home + "\\.catalyst"
        else:
            self.catalyst_root = catalyst_root
        self.exchange = exchange
        self.path = self.catalyst_root + "\\data\\exchanges\\" + exchange + "\\minute_bundle"
        self.reader = BcolzMinuteBarReader(self.path)

    def get_data(self, symbol=None, fields=None, start_dt=None, end_dt=None, current_time=None):
        """
        Method to retrieve the OHLCV minute data.

        Args:
            symbol (str or list of str): Symbol of the pair for which data is requested, or list thereof.
            fields (list of str): List containing the requested fields (among 'open', 'high', 'low', 'close', 'volume',
                'volume_quote').
            start_dt (pd.Timestamp): Start date of the period for which data is requested.
            end_dt (pd.Timestamp): End date of the period for which data is requested.
            current_time (pd.Timestamp, optional): The current time from the point of view of the algorithm/simulation.
                The method will raise an error if end_dt is after current_time, in order to eliminate any unforeseen
                look-ahead bias.

        Returns (pd.DataFrame or pd.Panel):
            If a single symbol is passed, the method returns a Pandas dataframe having the dates as an index and the
            fields as columns.
            If a list of symbols is passed, the method returns a Pandas panel having the fields along the item axis, the
            dates along the major axis and the pairs along the minor axis.
        """
        if current_time is not None:
            if end_dt > current_time:
                raise RuntimeError(f"The end time ({end_dt}) is in the future of the current time ({current_time}). "
                                   f"Proceeding would introduce look-ahead bias.")
        if isinstance(symbol, str):
            symbols = [symbol]
            return self.get_data_multiple_symbols(symbols, fields, start_dt, end_dt).iloc[:, :, 0]
        elif isinstance(symbol, list):
            return self.get_data_multiple_symbols(symbol, fields, start_dt, end_dt)

    @staticmethod
    def pre_handle_volume_quote(fields):
        adjusted_fields = fields.copy()
        if 'volume_quote' in fields:
            adjusted_fields.remove('volume_quote')
            if 'volume' not in fields:
                adjusted_fields.append('volume')
            if 'close' not in fields:
                adjusted_fields.append('close')
        return adjusted_fields

    def get_data_multiple_symbols(self, symbols, fields, start_dt, end_dt):
        """
        Gets OHLCV minute data from catalyst for a list of pairs.

        Args:
            See self.get_data.

        Returns (pd.Panel): Pandas panel having the fields along the item axis, the dates along the major axis and the
            pairs along the minor axis.
        """
        adjusted_fields = self.pre_handle_volume_quote(fields)
        sids = list(map(get_sid, symbols))
        data = self.reader.load_raw_arrays(fields=adjusted_fields, start_dt=start_dt, end_dt=end_dt, sids=sids)
        time_index = pd.DatetimeIndex(freq='1T', start=start_dt, end=end_dt)
        # Constructs a dataframe out of the data
        data_df = pd.Panel(data, items=adjusted_fields, major_axis=time_index, minor_axis=symbols)
        # Converts the volume from the base currency to the quote currency
        if 'volume' in fields and 'close' in fields:
            if 'volume_quote' in fields:
                data_df['volume_quote'] = np.multiply(data_df.volume, data_df.close)
                if 'volume' not in fields:
                    data_df.drop('volume', axis=0)
                if 'close' not in fields:
                    data_df.drop('close', axis=0)
        return data_df
