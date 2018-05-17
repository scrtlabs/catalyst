import os
import random
import re
import shutil

import bcolz
import numpy as np
import pandas as pd
from six import string_types


def merge_bundles(zsource, ztarget):
    """
    Merge
    Parameters
    ----------
    zsource
    ztarget

    Returns
    -------

    """
    # TODO: find a way to do this iteratively instead of in-memory
    df_source = zsource.todataframe()
    df_target = ztarget.todataframe()

    df = pd.concat(
        [df_source, df_target], ignore_index=True
    )  # type: pd.DataFrame
    df.drop_duplicates(inplace=True)
    df.set_index(['date', 'symbol'], drop=False, inplace=True)

    sanitize_df(df)

    dirname = os.path.basename(ztarget.rootdir)
    bak_dir = ztarget.rootdir.replace(dirname, '.{}'.format(dirname))
    shutil.move(ztarget.rootdir, bak_dir)

    z = bcolz.ctable.fromdataframe(df=df, rootdir=ztarget.rootdir)
    shutil.rmtree(bak_dir)
    return z


def sanitize_df(df):
    # Using a sampling method to identify dates for efficiency with
    # large datasets
    if len(df) > 100:
        indexes = random.sample(range(0, len(df) - 1), 100)
    elif len(df) > 1:
        indexes = range(0, len(df) - 1)
    else:
        indexes = [0, ]

    for column in df.columns:
        is_date = False
        for index in indexes:
            value = df[column].iloc[index]
            if not isinstance(value, string_types):
                continue

            # TODO: assuming that the date is at least daily
            exp = re.compile(r'^\d{4}-\d{2}-\d{2}.*$')
            matches = exp.findall(value)

            if matches:
                is_date = True
                break

        if is_date:
            df[column] = pd.to_datetime(df[column])

    return df


def safely_reduce_dtype(ser):  # pandas.Series or numpy.array
    orig_dtype = "".join(
        [x for x in ser.dtype.name if x.isalpha()])  # float/int
    mx = 1
    for val in ser.values:
        new_itemsize = np.min_scalar_type(val).itemsize
        if mx < new_itemsize:
            mx = new_itemsize
        if orig_dtype == 'int':
            mx = max(mx, 4)
    new_dtype = orig_dtype + str(mx * 8)
    return ser.astype(new_dtype)
