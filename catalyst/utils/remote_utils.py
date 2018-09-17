import base64
import pickle
import zlib
from uuid import UUID

import pandas as pd
from logbook import Logger


log = Logger('remote')

BACKTEST_PATH = '/backtest/run'
STATUS_PATH = '/status'

POST = 'POST'
GET = 'GET'
NONEXISTENT = 'nonexistent'

EXCEPTION_LOG = "please contact Catalyst support to fix this issue at\n" \
                "https://github.com/enigmampc/catalyst/issues/"


def prepare_args(file, text):
    """
    send the algo as a base64 decoded text object

    :param file: File
    :param text: str
    :return: None, text: str
    """

    if text:
        text = base64.b64encode(text)
    else:
        text = base64.b64encode(bytes(file.read(), 'utf-8')).decode('utf-8')
        file = None
    return file, text


def convert_date(date):
    """
    when transferring dates by json,
    converts it to str
    # any instances which need a conversion,
    # must be done here

    :param date:
    :return: str(date)
    """

    if isinstance(date, pd.Timestamp):
        return date.__str__()


def load_response(json_file):
    log_file = decompress_data(json_file['log']).decode('utf-8')
    data_df = None if json_file['data'] is None \
        else pickle.loads(decompress_data(json_file['data']))
    return data_df, log_file


def decompress_data(encoded_data):
    compressed_file = base64.b64decode(encoded_data)
    return zlib.decompress(compressed_file)


def handle_status(received_content):
    status = received_content['status']
    if status == NONEXISTENT:
        log.error(received_content['message'])
        return status

    perf, log_file = load_response(received_content)
    return status, perf, log_file


def is_valid_uuid(uuid_to_test, version=4):
    """
    Check if uuid_to_test is a valid UUID.

    Parameters
    ----------
    uuid_to_test : str
    version : {1, 2, 3, 4}

    Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.

    Examples
    --------
    >>> is_valid_uuid('c9bf9e57-1685-4c89-bafb-ff5af830be8a')
    True
    >>> is_valid_uuid('c9bf9e58')
    False
    """
    try:
        uuid_obj = UUID(uuid_to_test, version=version).hex
    except:
        return False

    return str(uuid_obj) == uuid_to_test
