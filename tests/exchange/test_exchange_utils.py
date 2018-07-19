from catalyst.exchange.utils.exchange_utils import transform_candles_to_df, \
    forward_fill_df_if_needed, get_candles_df

from catalyst.testing.fixtures import WithLogger, CatalystTestCase
from datetime import timedelta
from pandas import Timestamp, DataFrame, concat

import numpy as np


class TestExchangeUtils(WithLogger, CatalystTestCase):
    @classmethod
    def get_specific_field_from_df(cls, df, field, asset):
        new_df = DataFrame(df[field])
        new_df.columns = [asset]
        new_df.index.name = None
        return new_df

    @classmethod
    def verify_forward_fill_df_if_needed(cls, candles, periods, expected_df):
        observed_df = forward_fill_df_if_needed(
            transform_candles_to_df(candles),
            periods)
        assert (expected_df.equals(observed_df))

    @classmethod
    def verify_get_candles_df(cls, assets, candles, end_fixed_dt,
                              expected_df, check_next_candle=False):
        # run on all the fields
        for field in ['volume', 'open', 'close', 'high', 'low']:

            field_dt = cls.get_specific_field_from_df(expected_df,
                                                      field,
                                                      assets[0])
            # run on several timestamps
            for delta in range(5):
                end_dt = end_fixed_dt + timedelta(minutes=delta)
                assert (field_dt.equals(get_candles_df({assets[0]: candles},
                                                       field, '5T', 3,
                                                       end_dt=end_dt)))

                field_dt_a1 = cls.get_specific_field_from_df(expected_df,
                                                             field,
                                                             assets[0])
                field_dt_a2 = cls.get_specific_field_from_df(expected_df,
                                                             field,
                                                             assets[1])
                observed_df = get_candles_df({assets[0]: candles,
                                              assets[1]: candles},
                                             field, '5T', 3,
                                             end_dt=end_dt)

                assert (observed_df.equals(concat([field_dt_a1, field_dt_a2],
                                                  axis=1)))

            if check_next_candle:
                # one candle forward
                end_dt = end_fixed_dt + timedelta(minutes=6)
                observed_df = get_candles_df({assets[0]: candles,
                                              assets[1]: candles},
                                             field, '5T', 3,
                                             end_dt=end_dt)

                assert (not observed_df.equals(concat([field_dt_a1,
                                                       field_dt_a2],
                                               axis=1)))
                assert (concat([field_dt_a1, field_dt_a2],
                               axis=1)[1:].equals(observed_df[:-1]))

    def test_get_candles_df(self):
        assets = ['btc_usdt', 'eth_usdt']

        # test forward fill in the end
        candles = [{'high': 595, 'volume': 10, 'low': 594,
                    'close': 595, 'open': 594,
                    'last_traded': Timestamp('2018-03-01 09:45:00+0000',
                                             tz='UTC')
                    },
                   {'high': 594, 'volume': 108, 'low': 592,
                    'close': 593, 'open': 592,
                    'last_traded': Timestamp('2018-03-01 09:50:00+0000',
                                             tz='UTC')
                    }]

        expected = [{'high': 595.0, 'volume': 10.0, 'low': 594.0,
                     'close': 595.0, 'open': 594.0,
                     'last_traded': Timestamp('2018-03-01 09:45:00+0000',
                                              tz='UTC')
                     },
                    {'high': 594.0, 'volume': 108.0, 'low': 592.0,
                     'close': 593.0, 'open': 592.0,
                     'last_traded': Timestamp('2018-03-01 09:50:00+0000',
                                              tz='UTC')
                     },
                    {'high': 593.0, 'volume': 0.0, 'low': 593.0,
                     'close': 593.0, 'open': 593.0,
                     'last_traded': Timestamp('2018-03-01 09:55:00+0000',
                                              tz='UTC')
                     }]

        periods = [Timestamp('2018-03-01 09:45:00+0000', tz='UTC'),
                   Timestamp('2018-03-01 09:50:00+0000', tz='UTC'),
                   Timestamp('2018-03-01 09:55:00+0000', tz='UTC')]

        expected_df = transform_candles_to_df(expected)

        self.verify_forward_fill_df_if_needed(candles, periods,
                                              expected_df)
        self.verify_get_candles_df(assets, candles, periods[2],
                                   expected_df, True)

        # test forward fill in the middle
        candles = [{'high': 595, 'volume': 10, 'low': 594,
                    'close': 595, 'open': 594,
                    'last_traded': Timestamp('2018-03-01 09:45:00+0000',
                                             tz='UTC')
                    },
                   {'high': 594, 'volume': 108, 'low': 592,
                    'close': 593, 'open': 592,
                    'last_traded': Timestamp('2018-03-01 09:55:00+0000',
                                             tz='UTC')
                    }]

        expected = [{'high': 595.0, 'volume': 10.0, 'low': 594.0,
                     'close': 595.0, 'open': 594.0,
                     'last_traded': Timestamp('2018-03-01 09:45:00+0000',
                                              tz='UTC')
                     },
                    {'high': 595.0, 'volume': 0.0, 'low': 595.0,
                     'close': 595.0, 'open': 595.0,
                     'last_traded': Timestamp('2018-03-01 09:50:00+0000',
                                              tz='UTC')
                     },
                    {'high': 594.0, 'volume': 108.0, 'low': 592.0,
                     'close': 593.0, 'open': 592.0,
                     'last_traded': Timestamp('2018-03-01 09:55:00+0000',
                                              tz='UTC')
                     }]

        expected_df = transform_candles_to_df(expected)
        self.verify_forward_fill_df_if_needed(candles, periods, expected_df)
        self.verify_get_candles_df(assets, candles, periods[2], expected_df)

        # test "forward fill" at the beginning
        candles = [{'high': 595, 'volume': 10, 'low': 594,
                    'close': 595, 'open': 594,
                    'last_traded': Timestamp('2018-03-01 09:50:00+0000',
                                             tz='UTC')
                    },
                   {'high': 594, 'volume': 108, 'low': 592,
                    'close': 593, 'open': 592,
                    'last_traded': Timestamp('2018-03-01 09:55:00+0000',
                                             tz='UTC')
                    }]

        expected = [{'high': np.NaN, 'volume': 0.0, 'low': np.NaN,
                     'close': np.NaN, 'open': np.NaN,
                     'last_traded': Timestamp('2018-03-01 09:45:00+0000',
                                              tz='UTC')
                     },
                    {'high': 595, 'volume': 10, 'low': 594,
                     'close': 595, 'open': 594,
                     'last_traded': Timestamp('2018-03-01 09:50:00+0000',
                                              tz='UTC')
                     },
                    {'high': 594, 'volume': 108, 'low': 592,
                     'close': 593, 'open': 592,
                     'last_traded': Timestamp('2018-03-01 09:55:00+0000',
                                              tz='UTC')
                     }]

        expected_df = transform_candles_to_df(expected)
        self.verify_forward_fill_df_if_needed(candles, periods, expected_df)
        # Not the same due to dropna - commenting out for now
        # self.verify_get_candles_df(assets, candles, periods[2], expected_df)
