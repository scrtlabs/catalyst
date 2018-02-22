import os
import shutil

import bcolz
import pandas as pd


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

    dirname = os.path.basename(ztarget.rootdir)
    bak_dir = ztarget.rootdir.replace(dirname, '.{}'.format(dirname))
    os.rename(ztarget.rootdir, bak_dir)

    z = bcolz.ctable.fromdataframe(df=df, rootdir=ztarget.rootdir)
    shutil.rmtree(bak_dir)
    return z
