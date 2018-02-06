import os
import shutil

import bcolz


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
    df_source.set_index('date', drop=False, inplace=True)
    df_target = ztarget.todataframe()
    df_target.set_index('date', drop=False, inplace=True)

    df = df_target.merge(
        right=df_source,
        how='right',
    )  # type: pd.DataFrame

    dirname = os.path.basename(ztarget.rootdir)
    bak_dir = ztarget.rootdir.replace(dirname, '.{}'.format(dirname))
    os.rename(ztarget.rootdir, bak_dir)

    z = bcolz.ctable.fromdataframe(df=df, rootdir=ztarget.rootdir)
    shutil.rmtree(bak_dir)
    return z
