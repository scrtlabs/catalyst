import os
from catalyst.utils.paths import data_root


def get_exchange_folder(environ=None):
    if not environ:
        environ = os.environ

    root = data_root(environ)
