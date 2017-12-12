"""
Canonical path locations for catalyst data.

Paths are rooted at $ZIPLINE_ROOT if that environment variable is set.
Otherwise default to expanduser(~/.catalyst)
"""
from errno import EEXIST
import os
from os.path import exists, expanduser, join

import pandas as pd


def hidden(path):
    """Check if a path is hidden.

    Parameters
    ----------
    path : str
        A filepath.
    """
    return os.path.split(path)[1].startswith('.')


def ensure_directory(path):
    """
    Ensure that a directory named "path" exists.
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == EEXIST and os.path.isdir(path):
            return
        raise


def ensure_directory_containing(path):
    """
    Ensure that the directory containing `path` exists.

    This is just a convenience wrapper for doing::

        ensure_directory(os.path.dirname(path))
    """
    ensure_directory(os.path.dirname(path))


def ensure_file(path):
    """
    Ensure that a file exists. This will create any parent directories needed
    and create an empty file if it does not exist.

    Parameters
    ----------
    path : str
        The file path to ensure exists.
    """
    ensure_directory_containing(path)
    open(path, 'a+').close()  # touch the file


def update_modified_time(path, times=None):
    """
    Updates the modified time of an existing file. This will create any
    parent directories needed and create an empty file if it does not exist.

    Parameters
    ----------
    path : str
        The file path to update.
    times : tuple
        A tuple of size two; access time and modified time
    """
    ensure_directory_containing(path)
    os.utime(path, times)


def last_modified_time(path):
    """
    Get the last modified time of path as a Timestamp.
    """
    return pd.Timestamp(os.path.getmtime(path), unit='s', tz='UTC')


def modified_since(path, dt):
    """
    Check whether `path` was modified since `dt`.

    Returns False if path doesn't exist.

    Parameters
    ----------
    path : str
        Path to the file to be checked.
    dt : pd.Timestamp
        The date against which to compare last_modified_time(path).

    Returns
    -------
    was_modified : bool
        Will be ``False`` if path doesn't exists, or if its last modified date
        is earlier than or equal to `dt`
    """
    return exists(path) and last_modified_time(path) > dt


def catalyst_root(environ=None):
    """
    Get the root directory for all catalyst-managed files.

    For testing purposes, this accepts a dictionary to interpret as the os
    environment.

    Parameters
    ----------
    environ : dict, optional
        A dict to interpret as the os environment.

    Returns
    -------
    root : string
        Path to the catalyst root dir.
    """
    if environ is None:
        environ = os.environ

    root = environ.get('ZIPLINE_ROOT', None)
    if root is None:
        root = os.path.join(expanduser('~'), '.catalyst')

    return root


def catalyst_path(paths, environ=None):
    """
    Get a path relative to the catalyst root.

    Parameters
    ----------
    paths : list[str]
        List of requested path pieces.
    environ : dict, optional
        An environment dict to forward to catalyst_root.

    Returns
    -------
    newpath : str
        The requested path joined with the catalyst root.
    """
    return join(catalyst_root(environ=environ), *paths)


def default_extension(environ=None):
    """
    Get the path to the default catalyst extension file.

    Parameters
    ----------
    environ : dict, optional
        An environment dict to forwart to catalyst_root.

    Returns
    -------
    default_extension_path : str
        The file path to the default catalyst extension file.
    """
    return catalyst_path(['extension.py'], environ=environ)


def data_root(environ=None):
    """
    The root directory for catalyst data files.

    Parameters
    ----------
    environ : dict, optional
        An environment dict to forward to catalyst_root.

    Returns
    -------
    data_root : str
       The catalyst data root.
    """
    return catalyst_path(['data'], environ=environ)


def ensure_data_root(environ=None):
    """
    Ensure that the data root exists.
    """
    ensure_directory(data_root(environ=environ))


def data_path(paths, environ=None):
    """
    Get a path relative to the catalyst data directory.

    Parameters
    ----------
    paths : iterable[str]
        List of requested path pieces.
    environ : dict, optional
        An environment dict to forward to catalyst_root.

    Returns
    -------
    newpath : str
        The requested path joined with the catalyst data root.
    """
    return catalyst_path(['data'] + list(paths), environ=environ)


def cache_root(environ=None):
    """
    The root directory for catalyst cache files.

    Parameters
    ----------
    environ : dict, optional
        An environment dict to forward to catalyst_root.

    Returns
    -------
    cache_root : str
       The catalyst cache root.
    """
    return catalyst_path(['cache'], environ=environ)


def ensure_cache_root(environ=None):
    """
    Ensure that the data root exists.
    """
    ensure_directory(cache_root(environ=environ))


def cache_path(paths, environ=None):
    """
    Get a path relative to the catalyst cache directory.

    Parameters
    ----------
    paths : iterable[str]
        List of requested path pieces.
    environ : dict, optional
        An environment dict to forward to catalyst_root.

    Returns
    -------
    newpath : str
        The requested path joined with the catalyst cache root.
    """
    return catalyst_path(['cache'] + list(paths), environ=environ)
